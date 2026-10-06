"""
Clerk Authentication and User Mapping Service for ContentSignal.
Coordinates:
Frontend (Clerk Session Token) -> FastAPI (Clerk JWT Verification) -> DB User Record

Provides:
- Secure verification of Clerk RS256 session tokens.
- Support for Clerk SDK (clerk-backend-api), Clerk PEM Public Key, and cached JWKS.
- Stable user identity mapping: Clerk user ID (sub) -> ContentSignal User record.
- Tenant isolation and multi-user SaaS authorization helpers.
- Full testability with deterministic test credentials.
"""
import time
import logging
import base64
import json
from typing import Optional, Dict, Any, Tuple
import jwt
from jwt import PyJWKClient, ExpiredSignatureError, InvalidTokenError
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.config import (
    CLERK_SECRET_KEY,
    CLERK_PUBLISHABLE_KEY,
    CLERK_JWT_KEY,
    CLERK_JWKS_URL,
    CLERK_ISSUER,
    JWT_SECRET,
    JWT_ALGORITHM,
    APP_ENV,
)
from backend.database import get_db
from backend.models import User

logger = logging.getLogger("contentsignal.clerk_auth")

security = HTTPBearer(auto_error=False)

# In-memory JWKS cache to minimize external network requests
_JWKS_CACHE: Dict[str, Any] = {
    "keys": None,
    "expires_at": 0,
}

_JWKS_CACHE_TTL = 3600  # 1 hour


def _get_jwks_url() -> Optional[str]:
    """Resolves the appropriate JWKS endpoint for Clerk."""
    if CLERK_JWKS_URL:
        return CLERK_JWKS_URL

    # Derive from Publishable Key if available (format: pk_test_... or pk_live_...)
    if CLERK_PUBLISHABLE_KEY and "_" in CLERK_PUBLISHABLE_KEY:
        try:
            parts = CLERK_PUBLISHABLE_KEY.split("_", 2)
            if len(parts) >= 3:
                raw_domain = parts[2]
                # Decode base64 domain if needed
                padded = raw_domain + "=" * (-len(raw_domain) % 4)
                decoded_domain = base64.b64decode(padded).decode("utf-8").rstrip("$")
                if "." in decoded_domain:
                    return f"https://{decoded_domain}/.well-known/jwks.json"
        except Exception:
            pass

    # Default Clerk Backend API JWKS
    if CLERK_SECRET_KEY:
        return "https://api.clerk.com/v1/jwks"

    return None


def verify_clerk_token(token: str, request: Optional[Request] = None) -> Dict[str, Any]:
    """
    Verifies a Clerk session token and returns the decoded claims.
    Raises HTTPException(401) on failure.
    """
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clean_token = token.strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()

    # 1. Try clerk-backend-api authenticate_request if request object is available
    if request is not None and (CLERK_SECRET_KEY or CLERK_JWT_KEY):
        try:
            from clerk_backend_api import authenticate_request
            from clerk_backend_api.security.types import AuthenticateRequestOptions, AuthStatus

            opts = AuthenticateRequestOptions(
                secret_key=CLERK_SECRET_KEY or None,
                jwt_key=CLERK_JWT_KEY or None,
            )
            state = authenticate_request(request, opts)
            if state.status == AuthStatus.SIGNED_IN and state.payload:
                sub = state.payload.get("sub")
                if sub:
                    return state.payload
        except Exception as e:
            logger.debug("[CLERK_AUTH] clerk-backend-api authenticate_request fallback: %s", e)

    # 2. Networkless verification using CLERK_JWT_KEY (PEM public key)
    if CLERK_JWT_KEY:
        try:
            # Format public key with PEM header/footer if missing
            pem_key = CLERK_JWT_KEY.strip()
            if not pem_key.startswith("-----BEGIN"):
                pem_key = f"-----BEGIN PUBLIC KEY-----\n{pem_key}\n-----END PUBLIC KEY-----"
            
            payload = jwt.decode(
                clean_token,
                pem_key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
            if payload.get("sub"):
                return payload
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired. Please sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except InvalidTokenError as e:
            logger.debug("[CLERK_AUTH] PEM key decode error: %s", e)

    # 3. JWKS verification via PyJWKClient
    jwks_url = _get_jwks_url()
    if jwks_url:
        try:
            headers = {}
            if "api.clerk.com" in jwks_url and CLERK_SECRET_KEY:
                headers["Authorization"] = f"Bearer {CLERK_SECRET_KEY}"

            jwks_client = PyJWKClient(jwks_url, headers=headers, cache_keys=True, max_cached_keys=16)
            signing_key = jwks_client.get_signing_key_from_jwt(clean_token)

            payload = jwt.decode(
                clean_token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
            if payload.get("sub"):
                return payload
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired. Please sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.debug("[CLERK_AUTH] JWKS decode error: %s", e)

    # 4. Dev / Test / Transition fallback for local testing & fixtures
    # Allows HMAC or mock Clerk tokens during tests when no live Clerk instance is attached
    try:
        payload = jwt.decode(
            clean_token,
            JWT_SECRET,
            algorithms=["HS256", "RS256"],
            options={"verify_signature": False if (APP_ENV in ("test", "development") and clean_token.startswith("mock_clerk_")) else True, "verify_aud": False},
        )
        sub = payload.get("sub") or payload.get("clerk_user_id") or payload.get("uid")
        if sub:
            payload["sub"] = str(sub)
            return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        pass

    # Special handling for mock test tokens formatted as "mock_clerk_token_<user_id>"
    if APP_ENV in ("test", "development") and clean_token.startswith("mock_clerk_token_"):
        mock_uid = clean_token.replace("mock_clerk_token_", "")
        return {
            "sub": mock_uid,
            "email": f"{mock_uid}@example.com",
            "full_name": f"Mock User {mock_uid}",
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired session token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_or_create_clerk_user(db: Session, clerk_user_id: str, claims: Dict[str, Any]) -> User:
    """
    Safely resolves or provisions the ContentSignal User record mapped to the Clerk User ID.
    Guarantees that Clerk User ID is the stable external identity.
    """
    # 1. Check if token contains internal uid claim (e.g. transitional/testing tokens)
    uid = claims.get("uid")
    if uid:
        user = db.query(User).filter(User.id == uid).first()
        if user:
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account")
            if not user.clerk_user_id:
                user.clerk_user_id = clerk_user_id
                db.commit()
                db.refresh(user)
            return user

    # 2. Direct lookup by clerk_user_id
    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    if user:
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account")
        if not user.email and "@" in clerk_user_id:
            user.email = clerk_user_id
            db.commit()
            db.refresh(user)
        return user

    # 3. Resolve email and identifiers from claims
    email = claims.get("email") or claims.get("primary_email_address")
    if not email and "@" in clerk_user_id:
        email = clerk_user_id
    elif not email and "email_addresses" in claims and isinstance(claims["email_addresses"], list) and len(claims["email_addresses"]) > 0:
        first_email = claims["email_addresses"][0]
        email = first_email if isinstance(first_email, str) else first_email.get("email_address")

    clean_email = str(email).lower().strip() if email else None
    mobile = claims.get("phone_number") or claims.get("mobile_number")
    if not mobile and not clean_email and clerk_user_id.startswith("+"):
        mobile = clerk_user_id
    clean_mobile = str(mobile).strip() if mobile else None

    # Link existing user by email or mobile if previously created (e.g. starter/admin account)
    existing_user = None
    if clean_email:
        existing_user = db.query(User).filter(User.email == clean_email).first()
    if not existing_user and clean_mobile:
        existing_user = db.query(User).filter(User.mobile_number == clean_mobile).first()

    if existing_user:
        existing_user.clerk_user_id = clerk_user_id
        if not existing_user.is_verified:
            existing_user.is_verified = True
        db.commit()
        db.refresh(existing_user)
        return existing_user

    # Provision new user record for this Clerk identity
    full_name = claims.get("full_name") or claims.get("name")
    if not full_name:
        fname = claims.get("first_name", "")
        lname = claims.get("last_name", "")
        full_name = f"{fname} {lname}".strip() or None

    new_user = User(
        clerk_user_id=clerk_user_id,
        email=clean_email,
        mobile_number=clean_mobile,
        full_name=full_name,
        is_active=True,
        is_verified=True,
        onboarded=True,
        hashed_password="",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info("[CLERK_AUTH] Provisioned new ContentSignal user record %d for Clerk ID %s", new_user.id, clerk_user_id)
    return new_user


def get_current_clerk_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI Dependency for protected routes.
    1. Validates the Clerk session token from the Authorization header.
    2. Extracts the verified Clerk user ID (sub).
    3. Resolves the database User record.
    4. Enforces account active check.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = verify_clerk_token(credentials.credentials, request=request)
    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject identity",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return get_or_create_clerk_user(db, clerk_user_id, claims)


def get_optional_clerk_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    FastAPI Dependency for optional routes.
    Returns the User if valid Clerk token provided, otherwise None.
    """
    if not credentials or not credentials.credentials:
        return None

    try:
        claims = verify_clerk_token(credentials.credentials, request=request)
        clerk_user_id = claims.get("sub")
        if not clerk_user_id:
            return None
        return get_or_create_clerk_user(db, clerk_user_id, claims)
    except HTTPException:
        return None
    except Exception as e:
        logger.debug("[CLERK_AUTH] Optional auth failure: %s", e)
        return None
