"""
Authentication Router for ContentSignal.
Coordinates:
AUTH FRONTEND -> AUTH API -> AUTH SERVICE -> OTP SERVICE -> EMAIL/SMS PROVIDER -> USER DATABASE

Preserves all legacy endpoints for backward compatibility while providing full support for:
- Strict password policy enforcement.
- Pending account creation.
- Dual Email & Mobile Login.
- Decoupled Email OTP & Mobile OTP verification.
- Changing contact info on pending verification.
- Diagnostic email endpoints (/email-status, /verify-smtp, /test-email).
"""
import time
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    SignUpInitiateRequest,
    SignUpVerifyRequest,
    VerifyMobileOTPRequest,
    ResendMobileOTPRequest,
    ChangeContactRequest,
    LoginOTPInitiateRequest,
    LoginOTPVerifyRequest,
    TestEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
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
from backend.email_service import (
    send_verification_email,
    get_email_provider_status,
    verify_smtp_connection,
    verify_resend_connection,
    test_send_email,
    mask_email_address,
    logger,
)
from backend.sms_service import send_sms_otp, mask_mobile_number, get_sms_provider
from backend.otp_service import (
    generate_6digit_otp,
    hash_otp,
    verify_otp_candidate,
    check_rate_limits,
    record_otp_dispatch,
    verify_and_consume_email_otp,
    verify_and_consume_mobile_otp,
    MAX_OTP_ATTEMPTS,
)
from backend.auth_service import AuthService, validate_password_strength

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Cooldown tracking for resend requests (legacy alias for tests)
RESEND_COOLDOWNS: Dict[str, float] = {}
FAILED_LOGIN_ATTEMPTS: Dict[str, list] = {}
HOURLY_OTP_SENDS: Dict[str, list] = {}
OTP_EXPIRY_MINUTES = 10
RESEND_COOLDOWN_SECONDS = 60


def mask_email(email: str) -> str:
    return mask_email_address(email)


COMMON_PASSWORDS = {
    "password", "password123", "password1", "12345678", "123456789", "qwerty123",
    "admin123", "letmein123", "welcome123", "contentsignal", "contentsignal123"
}


def is_strong_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if " " in password:
        return False
    if password.lower() in COMMON_PASSWORDS:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_letter and has_digit


def check_otp_rate_limits(identifier: str) -> None:
    check_rate_limits(identifier)


def record_otp_send(identifier: str) -> None:
    record_otp_dispatch(identifier)
    RESEND_COOLDOWNS[identifier.lower().strip()] = time.time()


def _verify_and_consume_otp(user: User, submitted_otp: str, db: Session) -> None:
    """Legacy helper for backward compatibility in existing tests."""
    verify_and_consume_email_otp(user, submitted_otp, db)


# =========================================================================
# Rebuilt Authentication Endpoints (Phases 3 - 17)
# =========================================================================

@router.post("/signup-initiate")
def signup_initiate(req: SignUpInitiateRequest, db: Session = Depends(get_db)):
    """Phase 3 & 4: Initiate user sign up with pending state, password policy, and OTP dispatch."""
    return AuthService.initiate_signup(
        db=db,
        full_name=req.full_name,
        email=req.email,
        password=req.password,
        confirm_password=req.confirm_password,
        mobile_number=req.mobile_number,
        country_code=req.country_code or "+91",
        terms_accepted=req.terms_accepted if req.terms_accepted is not None else True,
        send_email_fn=send_verification_email,
        send_sms_fn=send_sms_otp,
    )


@router.post("/signup-verify")
def signup_verify(req: SignUpVerifyRequest, db: Session = Depends(get_db)):
    """Phase 5 & 11: Verify signup Email OTP and activate account."""
    return AuthService.verify_email_otp(db, req.email, req.otp)


@router.post("/signup-verify-email")
def signup_verify_email(req: SignUpVerifyRequest, db: Session = Depends(get_db)):
    """Phase 11: Dedicated endpoint to verify Email OTP."""
    return AuthService.verify_email_otp(db, req.email, req.otp)


@router.post("/signup-verify-mobile")
def signup_verify_mobile(req: VerifyMobileOTPRequest, db: Session = Depends(get_db)):
    """Phase 11: Dedicated endpoint to verify Mobile SMS OTP."""
    return AuthService.verify_mobile_otp(db, req.identifier, req.otp)


@router.post("/resend-email-otp")
def resend_email_otp(req: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Phase 5: Resend Email OTP with 60-second cooldown."""
    return AuthService.resend_email_otp(db, req.email, send_email_fn=send_verification_email)


@router.post("/resend-mobile-otp")
def resend_mobile_otp(req: ResendMobileOTPRequest, db: Session = Depends(get_db)):
    """Phase 6: Resend Mobile OTP with 60-second cooldown."""
    return AuthService.resend_mobile_otp(db, req.identifier, send_sms_fn=send_sms_otp)


@router.post("/change-contact")
def change_contact(req: ChangeContactRequest, db: Session = Depends(get_db)):
    """Phase 12: Change pending email or mobile contact info and invalidate old OTP."""
    return AuthService.change_contact(
        db=db,
        current_email=req.current_email,
        new_email=req.new_email,
        new_mobile=req.new_mobile,
        country_code=req.country_code or "+91",
        send_email_fn=send_verification_email,
    )


@router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    """Phase 13: Normal Login with Email OR Mobile + Password (No OTP required)."""
    ident = (req.identifier or req.email or "").strip()
    if not ident:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or mobile number is required.",
        )
    return AuthService.login(db, ident, req.password, remember_me=bool(req.remember_me))


@router.post("/login-otp-initiate")
def login_otp_initiate(req: LoginOTPInitiateRequest, db: Session = Depends(get_db)):
    """Phase 14: Optional Login with OTP - Request OTP."""
    ident = req.identifier.strip()
    user = db.query(User).filter(
        User.email == ident.lower() if "@" in ident else User.mobile_number == ident
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="No registered account found.")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your account before logging in.")

    check_rate_limits(ident)
    otp = generate_6digit_otp()
    user.verification_token = hash_otp(otp)
    user.verification_token_expires_at = datetime.utcnow() + timedelta(minutes=10)
    user.otp_attempts = 0
    db.commit()

    if "@" in ident:
        delivery = send_verification_email(user.email, otp, user.full_name)
    else:
        delivery = send_sms_otp(user.mobile_number, otp, user.country_code or "+91")

    if not delivery.get("success"):
        raise HTTPException(status_code=500, detail="Unable to send login verification code.")

    record_otp_dispatch(ident)
    return {"success": True, "message": "Login verification code sent."}


@router.post("/login-otp-verify")
def login_otp_verify(req: LoginOTPVerifyRequest, db: Session = Depends(get_db)):
    """Phase 14: Optional Login with OTP - Verify OTP & Authenticate."""
    ident = req.identifier.strip()
    user = db.query(User).filter(
        User.email == ident.lower() if "@" in ident else User.mobile_number == ident
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="No registered account found.")

    verify_and_consume_email_otp(user, req.otp, db)
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


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Phase 15: Forgot password OTP initiation."""
    ident = (req.identifier or req.email or "").strip()
    if not ident:
        return {"success": True, "message": "If an account exists, a reset code has been sent."}
    return AuthService.forgot_password(db, ident, send_email_fn=send_verification_email)


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Phase 15: Reset password with OTP."""
    ident = (req.identifier or req.email or "").strip()
    if not ident:
        raise HTTPException(status_code=400, detail="Email or mobile is required.")
    return AuthService.reset_password(db, ident, req.otp, req.new_password, req.confirm_password)


# =========================================================================
# Diagnostic & Health Endpoints (Phase 24)
# =========================================================================

@router.get("/email-status")
def get_email_status():
    """Phase 24: Non-sensitive diagnostic status for email & SMS providers."""
    return get_email_provider_status()


@router.get("/verify-smtp")
def check_smtp_connection():
    """Phase 24: Test live SMTP connection without leaking credentials."""
    return verify_smtp_connection()


@router.get("/verify-resend")
def check_resend_connection():
    """Phase 24: Test live Resend API connection with delivered@resend.dev without leaking credentials."""
    return verify_resend_connection()


@router.post("/test-email")
def send_test_email(req: TestEmailRequest):
    """
    Phase 24: Safe diagnostic endpoint to test email dispatch.
    Allows delivered@resend.dev in all environments.
    """
    target = req.email.strip().lower()
    if APP_ENV == "production" and not DEV_OTP_MODE and target != "delivered@resend.dev":
        raise HTTPException(
            status_code=403,
            detail="Diagnostics test endpoint disabled in production for arbitrary recipients. Use delivered@resend.dev to test Resend."
        )
    return test_send_email(req.email)


# =========================================================================
# Backward Compatibility Endpoints for Existing Test Suite
# =========================================================================

@router.post("/register")
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """Legacy registration endpoint preserved for existing integration tests."""
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

    is_auto_verified = (
        req.email == "demo@contentintelligence.ai" or 
        req.email.endswith("@editorial.ai") or
        req.email.endswith("@test.com")
    )
    
    verification_token = f"{secrets.randbelow(900000) + 100000}"
    token_expires = datetime.utcnow() + timedelta(hours=24)

    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=(req.full_name.strip() if req.full_name and req.full_name.strip() else None),
        is_active=True,
        is_verified=is_auto_verified,
        email_verified=is_auto_verified,
        verification_token=None if is_auto_verified else verification_token,
        verification_token_expires_at=None if is_auto_verified else token_expires,
        otp_attempts=0,
        onboarded=is_auto_verified,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    email_delivery = None
    if not is_auto_verified:
        email_delivery = send_verification_email(user.email, verification_token, user.full_name)
        RESEND_COOLDOWNS[user.email] = time.time()

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
    """Legacy email verification endpoint."""
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
    user.email_verified = True
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


@router.post("/send-otp")
def send_otp(req: SendOTPRequest, db: Session = Depends(get_db)):
    """Legacy send-otp endpoint preserved for test suite."""
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
    new_otp = f"{secrets.randbelow(900000) + 100000}"
    token_expires = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)

    if not user:
        user = User(
            email=email,
            hashed_password=hash_password(secrets.token_urlsafe(16)),
            full_name=req.full_name.strip() if req.full_name else None,
            is_active=True,
            is_verified=False,
            verification_token=new_otp,
            verification_token_expires_at=token_expires,
            otp_attempts=0,
            onboarded=False,
        )
        db.add(user)
    else:
        user.verification_token = new_otp
        user.verification_token_expires_at = token_expires
        user.otp_attempts = 0

    db.commit()
    db.refresh(user)
    RESEND_COOLDOWNS[email] = now

    email_delivery = send_verification_email(user.email, new_otp, user.full_name)
    if email_delivery and not email_delivery.get("success"):
        err_code = email_delivery.get("code") or "EMAIL_DELIVERY_FAILED"
        err_msg = email_delivery.get("message") or "Unable to send verification code. Please try again."
        resend_err = email_delivery.get("resend_error") or ""
        logger.error("[AUTH] /send-otp delivery failed for %s: [%s] %s", mask_email(user.email), err_code, err_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to send verification code. Please try again.",
            headers={
                "X-Error-Code": str(err_code),
                "X-Error-Reason": str(resend_err or err_msg)[:200],
            },
        )

    safe_token = new_otp if (DEV_OTP_MODE or (email_delivery and email_delivery.get("provider") == "development_fallback")) else None
    return {
        "success": True,
        "message": f"Verification code sent to {mask_email(user.email)}.",
        "email": user.email,
        "masked_email": mask_email(user.email),
        "is_verified": user.is_verified,
        "verification_token": safe_token,
        "dev_otp": safe_token,
        "email_delivery": email_delivery,
    }


@router.post("/verify-otp")
def verify_otp(req: VerifyOTPRequest, db: Session = Depends(get_db)):
    """Legacy verify-otp endpoint preserved for test suite."""
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

    _verify_and_consume_otp(user, req.otp, db)
    user.is_verified = True
    user.email_verified = True
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
        "message": "Email verified successfully."
    }


@router.post("/resend-verification")
def resend_verification(req: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Legacy resend-verification endpoint."""
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


@router.post("/cancel-verification")
def cancel_verification(req: CancelVerificationRequest, db: Session = Depends(get_db)):
    email = req.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if user and not user.is_verified:
        user.verification_token = None
        user.verification_token_expires_at = None
        user.otp_attempts = 0
        db.commit()
    return {"success": True, "message": "Verification session cleared."}


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


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user
