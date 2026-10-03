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


def test_resend_https_api_dispatch_called_and_smtp_not_touched():
    """Verify that EMAIL_PROVIDER=resend executes HTTPS REST API over port 443 and NEVER touches SMTP."""
    import httpx
    import smtplib

    with patch("backend.email_service.EMAIL_PROVIDER", "resend"), \
         patch("backend.email_service.RESEND_API_KEY", "re_live_test_dummy_key_123"), \
         patch("backend.email_service.SMTP_HOST", "smtp.gmail.com"), \
         patch("backend.email_service.SMTP_PORT", 587), \
         patch("backend.email_service.SMTP_USER", "unused_smtp@gmail.com"), \
         patch("backend.email_service.SMTP_PASSWORD", "unused_pass"), \
         patch("backend.email_service.EMAIL_FROM", "noreply@contentsignal.ai"), \
         patch("backend.email_service.EMAIL_FROM_NAME", "ContentSignal"), \
         patch("smtplib.SMTP") as mock_smtp, \
         patch("smtplib.SMTP_SSL") as mock_smtp_ssl, \
         patch("httpx.Client.post") as mock_http_post:

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "msg_resend_prod_123"}
        mock_http_post.return_value = mock_resp

        from backend.email_service import send_verification_email
        res = send_verification_email("customer@example.com", "882314", "Jane Doe")

        # 1. Assert Resend success response
        assert res["success"] is True
        assert res["provider"] == "resend"
        assert res["delivery_id"] == "msg_resend_prod_123"

        # 2. Assert HTTP call was sent to Resend REST API (HTTPS port 443)
        assert mock_http_post.called
        call_url = mock_http_post.call_args[0][0]
        call_headers = mock_http_post.call_args[1]["headers"]
        call_payload = mock_http_post.call_args[1]["json"]

        assert call_url == "https://api.resend.com/emails"
        assert call_headers["Authorization"] == "Bearer re_live_test_dummy_key_123"
        assert call_payload["to"] == ["customer@example.com"]
        assert "ContentSignal <noreply@contentsignal.ai>" in call_payload["from"]
        assert "882314" in call_payload["text"]

        # 3. Assert SMTP was strictly NEVER touched/attempted
        mock_smtp.assert_not_called()
        mock_smtp_ssl.assert_not_called()


def test_resend_sender_bracketed_name_handling():
    """Verify bracketed names with public or custom domains resolve safely."""
    from backend.config import get_effective_email_from

    # Bracketed Gmail name -> fallback to onboarding@resend.dev
    with patch("backend.config._raw_configured_from", "ContentSignal Support <anjali.56bn@gmail.com>"):
        assert get_effective_email_from("resend") == "onboarding@resend.dev"

    # Bracketed custom domain -> preserve clean domain
    with patch("backend.config._raw_configured_from", "ContentSignal Support <team@contentsignal.ai>"):
        assert get_effective_email_from("resend") == "team@contentsignal.ai"


def test_verify_resend_endpoint_success():
    """Test /api/auth/verify-resend with delivered@resend.dev mock success."""
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "re_delivered_msg_777"}
    mock_client.post.return_value = mock_resp

    with patch("backend.email_service.RESEND_API_KEY", "re_mock_test_key_valid"), \
         patch("backend.email_service.httpx.Client", return_value=mock_client):

        res = client.get("/api/auth/verify-resend")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["code"] == "OK"
        assert data["delivery_id"] == "re_delivered_msg_777"
        assert data["recipient"] == "delivered@resend.dev"
        assert "re_mock_test_key_valid" not in str(data)

        # Confirm exact URL and headers
        call_url = mock_client.post.call_args[0][0]
        call_headers = mock_client.post.call_args[1]["headers"]
        call_json = mock_client.post.call_args[1]["json"]
        assert call_url == "https://api.resend.com/emails"
        assert call_headers["Authorization"] == "Bearer re_mock_test_key_valid"
        assert call_json["to"] == ["delivered@resend.dev"]


def test_verify_resend_endpoint_handles_403_safely():
    """Test /api/auth/verify-resend reports Resend 403 error without leaking credentials."""
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.json.return_value = {
        "statusCode": 403,
        "message": "You can only send testing emails to your own email address",
        "name": "validation_error"
    }
    mock_client.post.return_value = mock_resp

    with patch("backend.email_service.RESEND_API_KEY", "re_mock_test_key_valid"), \
         patch("backend.email_service.httpx.Client", return_value=mock_client):

        res = client.get("/api/auth/verify-resend")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is False
        assert data["status_code"] == 403
        assert data["code"] == "RESEND_403"
        assert "You can only send testing emails" in data["message"]
        assert "re_mock_test_key_valid" not in str(data)


def test_send_otp_propagates_resend_error_headers_safely():
    """Verify that when Resend returns 403, /api/auth/send-otp sets diagnostic headers without leaking in body."""
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.json.return_value = {
        "statusCode": 403,
        "message": "You can only send testing emails to your own email address (owner@gmail.com).",
        "name": "validation_error"
    }
    mock_client.post.return_value = mock_resp

    with patch("backend.email_service.EMAIL_PROVIDER", "resend"), \
         patch("backend.email_service.RESEND_API_KEY", "re_mock_test_key_123"), \
         patch("backend.email_service.httpx.Client", return_value=mock_client):

        res = client.post("/api/auth/send-otp", json={"email": "unverified_stranger@example.com"})
        assert res.status_code == 500
        # Body detail stays clean without status code leaking to public client
        assert "Unable to send verification code" in res.json()["detail"]
        assert "403" not in res.json()["detail"]
        # Diagnostic headers contain the structured error
        assert res.headers.get("x-error-code") == "RESEND_403"
        assert "owner@gmail.com" in res.headers.get("x-error-reason", "")
        # API key is NEVER leaked in body or headers
        assert "re_mock_test_key_123" not in res.text
        assert "re_mock_test_key_123" not in str(res.headers)


def test_test_email_allows_delivered_resend_dev_in_production():
    """Verify delivered@resend.dev is permitted on /api/auth/test-email in production."""
    with patch("backend.routers.auth.APP_ENV", "production"), \
         patch("backend.routers.auth.DEV_OTP_MODE", False), \
         patch("backend.email_service.send_verification_email") as mock_send:
        mock_send.return_value = {
            "success": True,
            "provider": "resend",
            "status_code": 200,
            "delivery_id": "test_delivered_123",
            "code": "OK",
            "message": "Verification email dispatched via Resend.",
        }

        # 1. delivered@resend.dev is permitted
        res = client.post("/api/auth/test-email", json={"email": "delivered@resend.dev"})
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert res.json()["delivery_id"] == "test_delivered_123"

        # 2. Arbitrary email is blocked in production
        res_blocked = client.post("/api/auth/test-email", json={"email": "stranger@gmail.com"})
        assert res_blocked.status_code == 403


def test_decoupled_email_signup_no_phone_required(db_session):
    """Verify that email signup requires NO phone number and activates immediately upon email OTP verification."""
    unique_email = f"email_only_{uuid.uuid4().hex[:8]}@example.com"
    mock_delivery = {"success": True, "provider": "resend", "delivery_id": "test_deliv_email"}

    with patch("backend.auth_service.send_verification_email", return_value=mock_delivery):
        # 1. Initiate signup without mobile number
        init_res = client.post("/api/auth/signup-initiate", json={
            "full_name": "Email Only User",
            "auth_type": "email",
            "email": unique_email,
            "password": "Password123!",
            "confirm_password": "Password123!",
            "terms_accepted": True,
        })
        assert init_res.status_code == 200
        init_data = init_res.json()
        assert init_data["success"] is True
        assert init_data["email"]["sent"] is True

        user = db_session.query(User).filter(User.email == unique_email).first()
        assert user is not None
        assert user.mobile_number is None
        assert user.is_verified is False

        # Set known OTP
        known_otp = "852963"
        user.verification_token = hash_otp(known_otp)
        user.verification_token_expires_at = datetime.utcnow() + timedelta(minutes=10)
        db_session.commit()

        # 2. Verify email OTP -> auto activates
        verify_res = client.post("/api/auth/signup-verify", json={
            "email": unique_email,
            "otp": known_otp,
        })
        assert verify_res.status_code == 200
        verify_data = verify_res.json()
        assert verify_data["success"] is True
        assert "access_token" in verify_data
        assert verify_data["user"]["is_verified"] is True
        assert verify_data["user"]["email_verified"] is True
        assert verify_data["user"]["mobile_verified"] is False


def test_decoupled_phone_signup_unconfigured_sms_rejected(db_session):
    """Verify that phone signup when SMS is unconfigured returns a clear 400 error without faking success."""
    unique_phone = f"98{uuid.uuid4().int % 100000000:08d}"
    with patch("backend.auth_service.get_sms_provider", return_value="unconfigured"):
        res = client.post("/api/auth/signup-initiate", json={
            "full_name": "Phone Unconfigured User",
            "auth_type": "phone",
            "mobile_number": unique_phone,
            "country_code": "+91",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "terms_accepted": True,
        })
        assert res.status_code == 400
        assert "SMS verification is not configured" in res.json()["detail"]


def test_decoupled_phone_signup_and_verify_success(db_session):
    """Verify phone signup with mock SMS provider creates user with email=None and activates upon SMS OTP verification."""
    unique_phone = f"97{uuid.uuid4().int % 100000000:08d}"
    mock_sms_delivery = {"success": True, "provider": "mock_twilio", "sid": "SMtest123"}

    with patch("backend.auth_service.get_sms_provider", return_value="twilio"), \
         patch("backend.routers.auth.send_sms_otp", return_value=mock_sms_delivery), \
         patch("backend.auth_service.send_sms_otp", return_value=mock_sms_delivery):

        # 1. Initiate phone signup without email
        init_res = client.post("/api/auth/signup-initiate", json={
            "full_name": "Phone Only User",
            "auth_type": "phone",
            "mobile_number": unique_phone,
            "country_code": "+91",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "terms_accepted": True,
        })
        assert init_res.status_code == 200
        init_data = init_res.json()
        assert init_data["success"] is True
        assert init_data["auth_type"] == "phone"

        user = db_session.query(User).filter(User.mobile_number == unique_phone).first()
        assert user is not None
        assert user.email is None
        assert user.is_verified is False

        # Set known mobile OTP
        known_otp = "741258"
        user.mobile_otp_token = hash_otp(known_otp)
        user.mobile_otp_expires_at = datetime.utcnow() + timedelta(minutes=5)
        db_session.commit()

        # 2. Verify mobile OTP -> auto activates
        verify_res = client.post("/api/auth/signup-verify-mobile", json={
            "identifier": unique_phone,
            "mobile_number": unique_phone,
            "otp": known_otp,
        })
        assert verify_res.status_code == 200
        verify_data = verify_res.json()
        assert verify_data["success"] is True
        assert "access_token" in verify_data
        assert verify_data["user"]["is_verified"] is True
        assert verify_data["user"]["mobile_verified"] is True

        # 3. Test Login with phone (with and without country code)
        login_res1 = client.post("/api/auth/login", json={
            "identifier": unique_phone,
            "password": "Password123!",
        })
        assert login_res1.status_code == 200
        assert "access_token" in login_res1.json()

        login_res2 = client.post("/api/auth/login", json={
            "identifier": f"+91{unique_phone}",
            "password": "Password123!",
        })
        assert login_res2.status_code == 200
        assert "access_token" in login_res2.json()




