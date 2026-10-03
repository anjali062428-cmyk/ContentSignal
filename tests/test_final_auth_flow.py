"""
Comprehensive Unit and Integration Tests for Final Authentication Flow.
Covers:
- Password-only normal login (No OTP required)
- Email OR Mobile login support
- Cryptographic OTP hashing (plaintext OTP never in DB)
- Signup with OTP verification & Resend dispatch
- Strict 5-attempt OTP lockout & token invalidation
- OTP expiration rejection
- Forgot password & Password reset with OTP
- Resend sender safety for public domains (@gmail.com -> onboarding@resend.dev)
- Resend error handling without secret leakage
- Backward compatibility for legacy users and OTP endpoints
"""
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import SessionLocal
from backend.models import User
from backend.auth import hash_password, verify_password
from backend.config import get_effective_email_from
from backend.routers.auth import hash_otp

client = TestClient(app)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_resend_sender_safety_public_domains():
    """Verify that public domains are automatically sanitized to onboarding@resend.dev for Resend."""
    with patch("backend.config._raw_configured_from", "anjali.56bn@gmail.com"):
        assert get_effective_email_from("resend") == "onboarding@resend.dev"

    with patch("backend.config._raw_configured_from", "test@yahoo.com"):
        assert get_effective_email_from("resend") == "onboarding@resend.dev"

    # Custom domain is preserved
    with patch("backend.config._raw_configured_from", "noreply@contentsignal.ai"):
        assert get_effective_email_from("resend") == "noreply@contentsignal.ai"

    # For SMTP, the configured address is preserved
    with patch("backend.config._raw_configured_from", "anjali.56bn@gmail.com"):
        assert get_effective_email_from("smtp") == "anjali.56bn@gmail.com"


def test_signup_initiate_and_verify_success(db_session):
    """Test full sign up flow: initiate -> OTP dispatched -> verify OTP -> JWT token returned."""
    unique_email = f"signup_test_{uuid.uuid4().hex[:8]}@example.com"
    mock_delivery = {"success": True, "provider": "resend", "delivery_id": "test_resend_123"}

    with patch("backend.routers.auth.send_verification_email", return_value=mock_delivery) as mock_send:
        # 1. Initiate sign up
        init_res = client.post("/api/auth/signup-initiate", json={
            "full_name": "Test Signer",
            "email": unique_email,
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
        })
        assert init_res.status_code == 200
        assert init_res.json()["success"] is True

        # Extract generated OTP passed to email service
        assert mock_send.called
        otp = mock_send.call_args[0][1]

        # Check DB state: verification_token must be the secure HASH, NOT plaintext!
        user = db_session.query(User).filter(User.email == unique_email).first()
        assert user is not None
        assert user.is_verified is False
        assert user.verification_token != otp
        assert user.verification_token == hash_otp(otp)

        # 2. Verify sign up with correct OTP
        verify_res = client.post("/api/auth/signup-verify", json={
            "email": unique_email,
            "otp": otp,
        })
        assert verify_res.status_code == 200
        data = verify_res.json()
        assert data["success"] is True
        assert "access_token" in data
        assert data["user"]["email"] == unique_email
        assert data["user"]["is_verified"] is True

        # Confirm DB state
        db_session.refresh(user)
        assert user.is_verified is True
        assert user.verification_token is None


def test_normal_login_requires_no_otp(db_session):
    """Normal login must authenticate via email + password without requiring any OTP."""
    unique_email = f"login_test_{uuid.uuid4().hex[:8]}@example.com"
    raw_password = "SecurePassword123!"

    user = User(
        email=unique_email,
        full_name="Password User",
        hashed_password=hash_password(raw_password),
        is_active=True,
        is_verified=True,
        onboarded=True,
    )
    db_session.add(user)
    db_session.commit()

    # Login with correct password
    res = client.post("/api/auth/login", json={
        "email": unique_email,
        "password": raw_password,
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == unique_email


def test_mobile_signup_and_login(db_session):
    """Sign up with mobile number and verify login using either email or mobile."""
    unique_email = f"mobile_user_{uuid.uuid4().hex[:8]}@example.com"
    unique_mobile = f"98{uuid.uuid4().int % 100000000:08d}"
    raw_password = "SecurePassword123!"

    with patch("backend.routers.auth.send_verification_email") as mock_send:
        mock_send.return_value = {"success": True, "provider": "smtp"}
        init_res = client.post("/api/auth/signup-initiate", json={
            "full_name": "Mobile User",
            "email": unique_email,
            "mobile_number": unique_mobile,
            "country_code": "+91",
            "password": raw_password,
            "confirm_password": raw_password,
        })
        assert init_res.status_code == 200
        otp = mock_send.call_args[0][1]

        # Verify account
        verify_res = client.post("/api/auth/signup-verify", json={
            "email": unique_email,
            "otp": otp,
        })
        assert verify_res.status_code == 200

    # 1. Login with Mobile Number
    mob_login = client.post("/api/auth/login", json={
        "identifier": unique_mobile,
        "password": raw_password,
    })
    assert mob_login.status_code == 200
    assert mob_login.json()["user"]["email"] == unique_email

    # 2. Login with Email
    email_login = client.post("/api/auth/login", json={
        "identifier": unique_email,
        "password": raw_password,
    })
    assert email_login.status_code == 200
    assert email_login.json()["user"]["email"] == unique_email
    assert email_login.status_code == 200
    assert email_login.json()["user"]["email"] == unique_email


def test_login_with_wrong_password_rejected(db_session):
    """Login with wrong password must return 401 with safe generic message."""
    unique_email = f"wrongpw_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        hashed_password=hash_password("CorrectPassword123"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    res = client.post("/api/auth/login", json={
        "email": unique_email,
        "password": "WrongPassword999",
    })
    assert res.status_code == 401
    assert "Invalid email/mobile or password" in res.json()["detail"]


def test_login_account_without_password_handled_gracefully(db_session):
    """An account registered without a password must guide the user to use Forgot Password."""
    unique_email = f"nopw_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        hashed_password="",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    res = client.post("/api/auth/login", json={
        "email": unique_email,
        "password": "AnyPassword123",
    })
    assert res.status_code == 400
    assert "Forgot Password" in res.json()["detail"]


def test_otp_strict_5_attempt_lockout_and_invalidation(db_session):
    """
    Submitting incorrect OTPs must decrement attempts.
    On the 5th failed attempt, the token must be permanently invalidated.
    """
    unique_email = f"lockout_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        full_name="Lockout User",
        hashed_password=hash_password("StrongPassword123!"),
        is_active=True,
        is_verified=False,
        verification_token=hash_otp("123456"),
        verification_token_expires_at=datetime.utcnow() + timedelta(minutes=10),
        otp_attempts=0,
    )
    db_session.add(user)
    db_session.commit()

    # Attempts 1 to 4: wrong OTP
    for attempt in range(1, 5):
        res = client.post("/api/auth/signup-verify", json={
            "email": unique_email,
            "otp": "000000",
        })
        assert res.status_code == 400
        remaining = 5 - attempt
        assert f"{remaining} attempt" in res.json()["detail"]

    # Attempt 5: 5th failure must trigger lockout & invalidate token
    res_5 = client.post("/api/auth/signup-verify", json={
        "email": unique_email,
        "otp": "000000",
    })
    assert res_5.status_code == 400
    assert "Too many incorrect attempts" in res_5.json()["detail"]

    # Verify DB state: token is completely cleared
    db_session.refresh(user)
    assert user.verification_token is None
    assert user.verification_token_expires_at is None

    # Attempt 6 (even with the original correct OTP) must be rejected
    res_6 = client.post("/api/auth/signup-verify", json={
        "email": unique_email,
        "otp": "123456",
    })
    assert res_6.status_code in (400, 429)
    assert "Too many" in res_6.json()["detail"] or "No pending" in res_6.json()["detail"]


def test_expired_otp_is_rejected(db_session):
    """Expired OTP codes must be invalidated and rejected."""
    unique_email = f"expired_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        hashed_password=hash_password("StrongPassword123!"),
        is_active=True,
        is_verified=False,
        verification_token=hash_otp("654321"),
        verification_token_expires_at=datetime.utcnow() - timedelta(minutes=1),  # Expired
        otp_attempts=0,
    )
    db_session.add(user)
    db_session.commit()

    res = client.post("/api/auth/signup-verify", json={
        "email": unique_email,
        "otp": "654321",
    })
    assert res.status_code == 400
    assert "expired" in res.json()["detail"].lower()


def test_forgot_password_and_reset_flow(db_session):
    """Full forgot password flow: request reset OTP -> reset password -> login with new password."""
    unique_email = f"forgot_{uuid.uuid4().hex[:8]}@example.com"
    old_pw = "OldPassword123!"
    new_pw = "NewSecurePassword456!"

    user = User(
        email=unique_email,
        full_name="Forgot User",
        hashed_password=hash_password(old_pw),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    mock_delivery = {"success": True, "provider": "resend", "delivery_id": "test_reset_resend"}
    with patch("backend.routers.auth.send_verification_email", return_value=mock_delivery) as mock_send:
        # 1. Request forgot password reset
        forgot_res = client.post("/api/auth/forgot-password", json={"email": unique_email})
        assert forgot_res.status_code == 200
        assert forgot_res.json()["success"] is True

        otp = mock_send.call_args[0][1]

        # 2. Reset password using OTP
        reset_res = client.post("/api/auth/reset-password", json={
            "email": unique_email,
            "otp": otp,
            "new_password": new_pw,
            "confirm_password": new_pw,
        })
        assert reset_res.status_code == 200
        assert reset_res.json()["success"] is True

        # 3. Old password no longer works
        old_login = client.post("/api/auth/login", json={"email": unique_email, "password": old_pw})
        assert old_login.status_code == 401

        # 4. New password works immediately
        new_login = client.post("/api/auth/login", json={"email": unique_email, "password": new_pw})
        assert new_login.status_code == 200
        assert "access_token" in new_login.json()


def test_resend_api_failure_does_not_leak_secrets(db_session):
    """When email delivery fails, API returns clean 500 without leaking secrets."""
    unique_email = f"resend_fail_{uuid.uuid4().hex[:8]}@example.com"
    failed_delivery = {
        "success": False,
        "provider": "resend",
        "code": "RESEND_403",
        "message": "Resend API error: HTTP 403 domain not verified"
    }

    with patch("backend.routers.auth.send_verification_email", return_value=failed_delivery):
        res = client.post("/api/auth/signup-initiate", json={
            "full_name": "Test User",
            "email": unique_email,
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
        })
        assert res.status_code == 500
        detail = res.json()["detail"]
        assert "Unable to send verification code" in detail
        # Secrets and provider details are strictly not leaked
        assert "re_" not in detail
        assert "RESEND_API_KEY" not in detail
        assert "403" not in detail


def test_provider_precedence_case1_smtp_explicit():
    """CASE 1: EMAIL_PROVIDER=smtp, RESEND_API_KEY exists, SMTP credentials exist -> provider = smtp"""
    with patch("backend.email_service.EMAIL_PROVIDER", "smtp"), \
         patch("backend.email_service.RESEND_API_KEY", "re_test_key_12345"), \
         patch("backend.email_service.SMTP_HOST", "smtp.gmail.com"), \
         patch("backend.email_service.SMTP_PORT", 587), \
         patch("backend.email_service.SMTP_USER", "testuser@gmail.com"), \
         patch("backend.email_service.SMTP_PASSWORD", "mock_app_pass_1234"), \
         patch("backend.email_service.EMAIL_FROM", "testuser@gmail.com"):
        
        from backend.email_service import get_email_provider, get_email_provider_status, get_email_provider_instance, SMTPProvider
        assert get_email_provider() == "smtp"
        assert isinstance(get_email_provider_instance(), SMTPProvider)
        status = get_email_provider_status()
        assert status["provider"] == "smtp"
        assert status["is_configured"] is True
        assert "onboarding@resend.dev" not in status["sender"]


def test_provider_precedence_case2_resend_explicit():
    """CASE 2: EMAIL_PROVIDER=resend, RESEND_API_KEY exists, SMTP credentials exist -> provider = resend"""
    with patch("backend.email_service.EMAIL_PROVIDER", "resend"), \
         patch("backend.email_service.RESEND_API_KEY", "re_test_key_12345"), \
         patch("backend.email_service.SMTP_HOST", "smtp.gmail.com"), \
         patch("backend.email_service.SMTP_PORT", 587), \
         patch("backend.email_service.SMTP_USER", "testuser@gmail.com"), \
         patch("backend.email_service.SMTP_PASSWORD", "mock_app_pass_1234"):
        
        from backend.email_service import get_email_provider, get_email_provider_status, get_email_provider_instance, ResendProvider
        assert get_email_provider() == "resend"
        assert isinstance(get_email_provider_instance(), ResendProvider)
        status = get_email_provider_status()
        assert status["provider"] == "resend"
        assert status["is_configured"] is True


def test_provider_precedence_case3_smtp_explicit_missing_credentials():
    """CASE 3: EMAIL_PROVIDER=smtp, RESEND_API_KEY exists, SMTP credentials missing -> provider = smtp, does NOT fall back to resend"""
    with patch("backend.email_service.EMAIL_PROVIDER", "smtp"), \
         patch("backend.email_service.RESEND_API_KEY", "re_test_key_12345"), \
         patch("backend.email_service.SMTP_HOST", ""), \
         patch("backend.email_service.SMTP_USER", ""), \
         patch("backend.email_service.SMTP_PASSWORD", ""):
        
        from backend.email_service import get_email_provider, get_email_provider_status, get_email_provider_instance, SMTPProvider
        assert get_email_provider() == "smtp"
        instance = get_email_provider_instance()
        assert isinstance(instance, SMTPProvider)
        status = get_email_provider_status()
        assert status["provider"] == "smtp"
        assert status["is_configured"] is False
        
        # Delivery must fail with SMTP error and NOT silently use Resend
        result = instance.send("user@example.com", "Test", "HTML", "Text")
        assert result["success"] is False
        assert result["provider"] == "smtp"
        assert result["code"] == "SMTP_NOT_CONFIGURED"


def test_provider_precedence_case4_resend_explicit_missing_credentials():
    """CASE 4: EMAIL_PROVIDER=resend, Resend credentials missing, SMTP exists -> provider = resend, does NOT fall back to smtp"""
    with patch("backend.email_service.EMAIL_PROVIDER", "resend"), \
         patch("backend.email_service.RESEND_API_KEY", ""), \
         patch("backend.email_service.SMTP_HOST", "smtp.gmail.com"), \
         patch("backend.email_service.SMTP_PORT", 587), \
         patch("backend.email_service.SMTP_USER", "testuser@gmail.com"), \
         patch("backend.email_service.SMTP_PASSWORD", "mock_app_pass_1234"):
        
        from backend.email_service import get_email_provider, get_email_provider_status, get_email_provider_instance, ResendProvider
        assert get_email_provider() == "resend"
        instance = get_email_provider_instance()
        assert isinstance(instance, ResendProvider)
        status = get_email_provider_status()
        assert status["provider"] == "resend"
        assert status["is_configured"] is False
        
        # Delivery must fail with Resend error and NOT silently use SMTP
        result = instance.send("user@example.com", "Test", "HTML", "Text")
        assert result["success"] is False
        assert result["provider"] == "resend"
        assert result["code"] == "RESEND_NOT_CONFIGURED"


def test_smtp_configuration_parameters_verified():
    """Verify SMTP initialization parameters matching Render production setup without exposing secrets."""
    with patch("backend.email_service.EMAIL_PROVIDER", "smtp"), \
         patch("backend.email_service.SMTP_HOST", "smtp.gmail.com"), \
         patch("backend.email_service.SMTP_PORT", 587), \
         patch("backend.email_service.SMTP_USER", "configured_user@gmail.com"), \
         patch("backend.email_service.SMTP_PASSWORD", "secret_pass_1234"), \
         patch("backend.email_service.SMTP_USE_TLS", True), \
         patch("backend.email_service.EMAIL_FROM", "configured_user@gmail.com"), \
         patch("backend.email_service.EMAIL_FROM_NAME", "ContentSignal"):
        
        from backend.email_service import get_email_provider, get_email_provider_status
        assert get_email_provider() == "smtp"
        status = get_email_provider_status()
        assert status["provider"] == "smtp"
        assert status["is_configured"] is True
        assert status["smtp_host_configured"] is True
        assert "configured_user@gmail.com" in status["sender"]
        # Password and sensitive secrets are NEVER exposed in status
        assert "secret_pass_1234" not in str(status)

