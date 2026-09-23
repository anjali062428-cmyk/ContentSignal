"""
Authentication Router with Email Verification, Strong Passwords, and Onboarding.
"""
import time
import secrets
from datetime import datetime, timedelta
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
    VerifyOTPRequest,
    SendOTPRequest,
    ResendVerificationRequest,
    CancelVerificationRequest,
    OnboardingRequest,
)
from backend.auth import hash_password, verify_password, create_access_token, get_current_user
from backend.config import APP_ENV, DEV_OTP_MODE
from backend.email_service import send_verification_email, get_email_provider_status, logger

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Cooldown tracking for resend requests: email -> timestamp
RESEND_COOLDOWNS: Dict[str, float] = {}

# Login attempt rate limiting: email -> list of failed attempt timestamps
FAILED_LOGIN_ATTEMPTS: Dict[str, list] = {}


def mask_email(email: str) -> str:
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


def is_strong_password(password: str) -> bool:
    if len(password) < 8:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_letter and has_digit


@router.post("/send-otp")
def send_otp(req: SendOTPRequest, db: Session = Depends(get_db)):
    """Generate and dispatch a 6-digit OTP code to the user's email."""
    email = req.email.lower().strip()
    now = time.time()
    last_sent = RESEND_COOLDOWNS.get(email, 0)
    cooldown_seconds = 30
    if now - last_sent < cooldown_seconds:
        remaining = int(cooldown_seconds - (now - last_sent))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {remaining} seconds before requesting another verification code."
        )

    user = db.query(User).filter(User.email == email).first()

    # Auto-verify demo and test suites
    is_auto_verified = (
        email == "demo@contentintelligence.ai" or 
        email.endswith("@editorial.ai") or
        email.endswith("@test.com")
    )
    
    new_otp = f"{secrets.randbelow(900000) + 100000}"
    token_expires = datetime.utcnow() + timedelta(minutes=5)

    if not user:
        # Auto-provision user account with random initial password hash
        user = User(
            email=email,
            hashed_password=hash_password(secrets.token_urlsafe(16)),
            full_name=(req.full_name.strip() if req.full_name and req.full_name.strip() else None),
            is_active=True,
            is_verified=is_auto_verified,
            verification_token=None if is_auto_verified else new_otp,
            verification_token_expires_at=None if is_auto_verified else token_expires,
            otp_attempts=0,
            onboarded=is_auto_verified,
        )
        db.add(user)
    else:
        if req.full_name and req.full_name.strip() and not user.full_name:
            user.full_name = req.full_name.strip()
        if not is_auto_verified:
            user.verification_token = new_otp
            user.verification_token_expires_at = token_expires
            user.otp_attempts = 0

    db.commit()
    db.refresh(user)

    logger.info("[OTP] generation: SUCCESS")
    logger.info("[OTP] storage: SUCCESS")

    RESEND_COOLDOWNS[email] = now

    email_delivery = None
    if not is_auto_verified:
        email_delivery = send_verification_email(user.email, new_otp, user.full_name)

    # If delivery failed, NEVER return false success
    delivery_failed = bool(email_delivery and not email_delivery.get("success"))
    if delivery_failed:
        code = email_delivery.get("code") or "OTP_EMAIL_FAILED"
        err_detail = email_delivery.get("message") or "Unable to send verification code. Please try again."
        logger.error("[EMAIL] send: FAILED")
        logger.error("[EMAIL] error code: %s", code)
        logger.error("[EMAIL] error message: %s", err_detail)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to send verification code. Please try again."
        )

    if email_delivery and email_delivery.get("success"):
        logger.info("[EMAIL] send: SUCCESS")
        logger.info("[EMAIL] provider message ID: %s", email_delivery.get("delivery_id") or "accepted")

    is_production = APP_ENV == "production"
    # Never expose OTP in production or when DEV_OTP_MODE is disabled
    safe_token = None
    if not is_production and not is_auto_verified:
        if DEV_OTP_MODE or (email_delivery and email_delivery.get("provider") == "development_fallback"):
            safe_token = new_otp
            logger.info("[DEV_OTP_MODE] Generated OTP for %s: %s", user.email, safe_token)

    msg = f"Verification code sent to {mask_email(user.email)}." if not is_auto_verified else "Account ready."

    return {
        "success": True,
        "message": msg,
        "email": user.email,
        "masked_email": mask_email(user.email),
        "is_verified": user.is_verified,
        "verification_token": safe_token,
        "dev_otp": safe_token,
        "email_delivery": email_delivery,
    }


@router.get("/verify-smtp")
def check_smtp_connection():
    """Diagnostic endpoint to test and verify SMTP connection and authentication safely."""
    from backend.email_service import verify_smtp_connection
    return verify_smtp_connection()


@router.post("/verify-otp")
def verify_otp(req: VerifyOTPRequest, db: Session = Depends(get_db)):
    """Verify 6-digit OTP code and return JWT access token."""
    email = req.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")

    if user.is_verified and not user.verification_token:
        token = create_access_token({"sub": user.email, "uid": user.id})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_verified": True,
                "onboarded": user.onboarded,
            },
            "message": "Email is already verified."
        }

    attempts = getattr(user, "otp_attempts", 0) or 0
    if attempts >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed verification attempts. Please request a new code."
        )

    clean_otp = req.otp.strip()
    if not user.verification_token or user.verification_token != clean_otp:
        user.otp_attempts = attempts + 1
        db.commit()
        remaining = max(0, 5 - (attempts + 1))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification code. {remaining} attempt{'s' if remaining != 1 else ''} remaining."
        )

    if user.verification_token_expires_at and user.verification_token_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code expired. Please request a new code."
        )

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    user.otp_attempts = 0
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email, "uid": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_verified": True,
            "onboarded": user.onboarded,
        },
        "message": "Email successfully verified."
    }


@router.post("/cancel-verification")
def cancel_verification(req: CancelVerificationRequest, db: Session = Depends(get_db)):
    """Clear and invalidate any active OTP session when switching emails."""
    email = req.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if user and not user.is_verified:
        user.verification_token = None
        user.verification_token_expires_at = None
        user.otp_attempts = 0
        db.commit()
    return {"success": True, "message": "Verification session cleared."}


@router.post("/register")
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    if not is_strong_password(req.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters and include at least one letter and one number."
        )

    if req.confirm_password is not None and req.password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match."
        )

    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered")

    # Auto-verify demo and test suites
    is_auto_verified = (
        req.email == "demo@contentintelligence.ai" or 
        req.email.endswith("@editorial.ai") or
        req.email.endswith("@test.com")
    )
    
    # 6-digit numeric token
    verification_token = f"{secrets.randbelow(900000) + 100000}"
    token_expires = datetime.utcnow() + timedelta(hours=24)

    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=(req.full_name.strip() if req.full_name and req.full_name.strip() else None),
        is_active=True,
        is_verified=is_auto_verified,
        verification_token=None if is_auto_verified else verification_token,
        verification_token_expires_at=None if is_auto_verified else token_expires,
        otp_attempts=0,
        onboarded=is_auto_verified,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Dispatch verification email if not auto-verified
    email_delivery = None
    if not is_auto_verified:
        email_delivery = send_verification_email(user.email, verification_token, user.full_name)
        RESEND_COOLDOWNS[user.email] = time.time()

    # In production, verification token is strictly NOT returned in API response
    is_production = APP_ENV == "production"
    safe_token = None if (is_auto_verified or is_production) else verification_token

    token = create_access_token({"sub": user.email, "uid": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "onboarded": user.onboarded,
        },
        "is_verified": user.is_verified,
        "masked_email": mask_email(user.email),
        "verification_token": safe_token,
        "dev_otp": safe_token,
        "email_delivery": email_delivery,
        "message": "Account created. A 6-digit confirmation code has been sent to your email." if not is_auto_verified else "Account ready.",
    }


@router.post("/verify-email")
def verify_email(req: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified and not user.verification_token:
        token = create_access_token({"sub": user.email, "uid": user.id})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_verified": True,
                "onboarded": user.onboarded,
            },
            "message": "Email is already verified."
        }

    attempts = getattr(user, "otp_attempts", 0) or 0
    if attempts >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed verification attempts. Please request a new code."
        )

    clean_token = req.token.strip()
    if not user.verification_token or user.verification_token != clean_token:
        user.otp_attempts = attempts + 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid verification code")

    if user.verification_token_expires_at and user.verification_token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new one.")

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    user.otp_attempts = 0
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email, "uid": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_verified": True,
            "onboarded": user.onboarded,
        },
        "message": "Email successfully verified."
    }


@router.post("/resend-verification")
def resend_verification(req: ResendVerificationRequest, db: Session = Depends(get_db)):
    now = time.time()
    last_sent = RESEND_COOLDOWNS.get(req.email, 0)
    cooldown_seconds = 30
    if now - last_sent < cooldown_seconds:
        remaining = int(cooldown_seconds - (now - last_sent))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {remaining} seconds before requesting another verification code."
        )

    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        return {"message": "Email is already verified.", "masked_email": mask_email(user.email)}

    new_token = f"{secrets.randbelow(900000) + 100000}"
    user.verification_token = new_token
    user.verification_token_expires_at = datetime.utcnow() + timedelta(hours=24)
    user.otp_attempts = 0
    db.commit()

    RESEND_COOLDOWNS[req.email] = now

    # Dispatch fresh verification email
    email_delivery = send_verification_email(user.email, new_token, user.full_name)

    is_production = APP_ENV == "production"
    safe_token = None if is_production else new_token

    return {
        "message": "New verification code sent to your email address.",
        "masked_email": mask_email(user.email),
        "verification_token": safe_token,
        "dev_otp": safe_token,
        "email_delivery": email_delivery,
    }


@router.get("/email-status")
def get_email_status():
    """Diagnostic status for the active email delivery provider."""
    return get_email_provider_status()


@router.post("/onboarding")
def complete_onboarding(
    req: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.onboarded = req.onboarded
    db.commit()
    db.refresh(current_user)
    return {
        "message": "Onboarding completed successfully",
        "onboarded": current_user.onboarded,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "is_verified": current_user.is_verified,
            "onboarded": current_user.onboarded,
        }
    }


@router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    now = time.time()
    attempts = [t for t in FAILED_LOGIN_ATTEMPTS.get(req.email, []) if now - t < 60]
    if len(attempts) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait 60 seconds before trying again."
        )

    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        attempts.append(now)
        FAILED_LOGIN_ATTEMPTS[req.email] = attempts
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if req.email in FAILED_LOGIN_ATTEMPTS:
        del FAILED_LOGIN_ATTEMPTS[req.email]

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your email address is not verified. Please verify your account before logging in."
        )

    token = create_access_token({"sub": user.email, "uid": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "onboarded": user.onboarded,
        },
    }


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user
