"""
Comprehensive Unit & Integration Tests for Email Verification and Delivery.
"""
import uuid
import smtplib
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import SessionLocal
from backend.models import User
from backend.email_service import (
    send_verification_email,
    get_email_provider,
    get_email_provider_status,
    verify_smtp_connection,
    mask_email_address,
)

client = TestClient(app)


def test_mask_email_address():
    assert mask_email_address("alex@example.com") == "a**x@example.com"
    assert mask_email_address("ab@example.com") == "a*@example.com"
    assert mask_email_address("a@example.com") == "a*@example.com"
    assert mask_email_address("john.doe@company.org") == "j******e@company.org"


def test_email_service_fallback_development():
    with patch("backend.email_service.RESEND_API_KEY", ""), \
         patch("backend.email_service.SMTP_HOST", ""), \
         patch("backend.email_service.APP_ENV", "development"):
        assert get_email_provider() == "development_fallback"
        res = send_verification_email("devuser@example.com", "654321", "Dev User")
        assert res["success"] is True
        assert res["provider"] == "development_fallback"
        assert res["delivery_id"] == "dev_simulated"


def test_email_service_fallback_production_unconfigured():
    with patch("backend.email_service.RESEND_API_KEY", ""), \
         patch("backend.email_service.SMTP_HOST", ""), \
         patch("backend.email_service.APP_ENV", "production"):
        res = send_verification_email("produser@example.com", "654321")
        assert res["success"] is False
        assert res["provider"] == "unconfigured"


def test_email_service_resend_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "resend_msg_abc123"}

    with patch("backend.email_service.RESEND_API_KEY", "re_test_valid_key"), \
         patch("backend.email_service.SMTP_HOST", ""), \
         patch("httpx.Client.post", return_value=mock_response) as mock_post:
        
        assert get_email_provider() == "resend"
        res = send_verification_email("recipient@company.org", "987654", "Recipient Name")
        
        assert res["success"] is True
        assert res["provider"] == "resend"
        assert res["delivery_id"] == "resend_msg_abc123"
        
        # Verify httpx payload
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == "Bearer re_test_valid_key"
        assert call_kwargs["json"]["to"] == ["recipient@company.org"]
        assert "987654" in call_kwargs["json"]["subject"]
        assert "987654" in call_kwargs["json"]["html"]
        assert "987654" in call_kwargs["json"]["text"]


def test_email_service_resend_api_error():
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = '{"message": "Domain not verified"}'

    with patch("backend.email_service.RESEND_API_KEY", "re_test_key"), \
         patch("httpx.Client.post", return_value=mock_response):
        
        res = send_verification_email("recipient@company.org", "987654")
        assert res["success"] is False
        assert res["provider"] == "resend"
        assert "403" in res["message"]


def test_email_service_smtp_success():
    mock_smtp_instance = MagicMock()
    with patch("backend.email_service.RESEND_API_KEY", ""), \
         patch("backend.email_service.SMTP_HOST", "smtp.testmail.com"), \
         patch("backend.email_service.SMTP_PORT", 587), \
         patch("backend.email_service.SMTP_USER", "smtp_user"), \
         patch("backend.email_service.SMTP_PASSWORD", "smtp_secret"), \
         patch("backend.email_service.SMTP_USE_TLS", True), \
         patch("smtplib.SMTP", return_value=mock_smtp_instance) as mock_smtp_cls:
        
        assert get_email_provider() == "smtp"
        res = send_verification_email("smtp_recipient@company.org", "112233", "SMTP User")
        
        assert res["success"] is True
        assert res["provider"] == "smtp"
        mock_smtp_cls.assert_called_once_with("smtp.testmail.com", 587, timeout=10)
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("smtp_user", "smtp_secret")
        mock_smtp_instance.sendmail.assert_called_once()
        mock_smtp_instance.quit.assert_called_once()


def test_email_service_smtp_failure():
    with patch("backend.email_service.RESEND_API_KEY", ""), \
         patch("backend.email_service.SMTP_HOST", "smtp.invalid-host.com"), \
         patch("backend.email_service.SMTP_PORT", 587), \
         patch("smtplib.SMTP", side_effect=smtplib.SMTPConnectError(421, "Connection refused")):
        
        res = send_verification_email("fail_recipient@company.org", "112233")
        assert res["success"] is False
        assert res["provider"] == "smtp"
        assert "Connection refused" in res["message"]


def test_email_provider_status_endpoint():
    res = client.get("/api/auth/email-status")
    assert res.status_code == 200
    data = res.json()
    assert "provider" in data
    assert "is_configured" in data
    assert "sender" in data
    assert "environment" in data


def test_register_flow_and_email_dispatch():
    new_email = f"verify_{uuid.uuid4().hex[:8]}@verifiedcorp.io"
    
    with patch("backend.routers.auth.send_verification_email") as mock_send:
        mock_send.return_value = {"success": True, "provider": "resend", "delivery_id": "test_id"}
        
        res = client.post("/api/auth/register", json={
            "email": new_email,
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "full_name": "Verified User",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["is_verified"] is False
        assert "masked_email" in data
        
        # Verify send_verification_email was called with user email and 6-digit code
        mock_send.assert_called_once()
        called_args = mock_send.call_args[0]
        assert called_args[0] == new_email
        assert len(called_args[1]) == 6
        assert called_args[1].isdigit()
        assert called_args[2] == "Verified User"


def test_resend_verification_and_cooldown():
    new_email = f"resend_{uuid.uuid4().hex[:8]}@resendcorp.io"
    
    # 1. Register
    reg_res = client.post("/api/auth/register", json={
        "email": new_email,
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
        "full_name": "Cooldown Test",
    })
    assert reg_res.status_code == 200
    
    # 2. Immediate resend should trigger 429 cooldown
    resend_1 = client.post("/api/auth/resend-verification", json={"email": new_email})
    assert resend_1.status_code == 429
    assert "seconds before requesting" in resend_1.json()["detail"]

    # 3. Simulate cooldown expiration
    from backend.routers.auth import RESEND_COOLDOWNS
    RESEND_COOLDOWNS[new_email] = 0.0

    with patch("backend.routers.auth.send_verification_email") as mock_send:
        mock_send.return_value = {"success": True, "provider": "smtp", "delivery_id": "smtp_test"}
        resend_ok = client.post("/api/auth/resend-verification", json={"email": new_email})
        assert resend_ok.status_code == 200
        assert "New verification code" in resend_ok.json()["message"]
        mock_send.assert_called_once()


def test_verification_code_lifecycle():
    new_email = f"lifecycle_{uuid.uuid4().hex[:8]}@lifecycledomain.com"
    
    # Register
    reg_res = client.post("/api/auth/register", json={
        "email": new_email,
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
    })
    assert reg_res.status_code == 200
    
    # Fetch token from database directly
    db = SessionLocal()
    user = db.query(User).filter(User.email == new_email).first()
    assert user is not None
    real_token = user.verification_token
    assert len(real_token) == 6
    db.close()

    # 1. Test invalid code (fails)
    res_bad = client.post("/api/auth/verify-email", json={
        "email": new_email,
        "token": "000000" if real_token != "000000" else "999999",
    })
    assert res_bad.status_code == 400
    assert "Invalid verification code" in res_bad.json()["detail"]

    # 2. Test expired code (fails)
    db = SessionLocal()
    user = db.query(User).filter(User.email == new_email).first()
    user.verification_token_expires_at = datetime.utcnow() - timedelta(hours=1)
    db.commit()
    db.close()

    res_expired = client.post("/api/auth/verify-email", json={
        "email": new_email,
        "token": real_token,
    })
    assert res_expired.status_code == 400
    assert "expired" in res_expired.json()["detail"].lower()

    # 3. Request fresh token via resend
    from backend.routers.auth import RESEND_COOLDOWNS
    RESEND_COOLDOWNS[new_email] = 0.0
    resend_res = client.post("/api/auth/resend-verification", json={"email": new_email})
    assert resend_res.status_code == 200

    db = SessionLocal()
    user = db.query(User).filter(User.email == new_email).first()
    fresh_token = user.verification_token
    db.close()

    # 4. Verify with fresh token (succeeds)
    verify_ok = client.post("/api/auth/verify-email", json={
        "email": new_email,
        "token": fresh_token,
    })
    assert verify_ok.status_code == 200
    assert "successfully verified" in verify_ok.json()["message"].lower()

    # 5. Verify again (already verified idempotence)
    verify_again = client.post("/api/auth/verify-email", json={
        "email": new_email,
        "token": fresh_token,
    })
    assert verify_again.status_code == 200
    assert "already verified" in verify_again.json()["message"].lower()

    # 6. Resend for already verified account
    RESEND_COOLDOWNS[new_email] = 0.0
    resend_verified = client.post("/api/auth/resend-verification", json={"email": new_email})
    assert resend_verified.status_code == 200
    assert "already verified" in resend_verified.json()["message"].lower()


def test_production_security_never_exposes_token():
    new_email = f"prodsec_{uuid.uuid4().hex[:8]}@productionsecurity.com"
    
    with patch("backend.routers.auth.APP_ENV", "production"):
        res = client.post("/api/auth/register", json={
            "email": new_email,
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        })
        assert res.status_code == 200
        # In production mode, verification_token must be strictly None in response
        assert res.json()["verification_token"] is None

        from backend.routers.auth import RESEND_COOLDOWNS
        RESEND_COOLDOWNS[new_email] = 0.0
        
        res_resend = client.post("/api/auth/resend-verification", json={"email": new_email})
        assert res_resend.status_code == 200
        assert res_resend.json()["verification_token"] is None


def test_send_and_verify_otp_end_to_end():
    otp_email = f"otpuser_{uuid.uuid4().hex[:8]}@example.com"
    
    with patch("backend.routers.auth.send_verification_email") as mock_send:
        mock_send.return_value = {"success": True, "provider": "development_fallback", "delivery_id": "simulated"}
        
        # 1. User enters email -> Send OTP
        send_res = client.post("/api/auth/send-otp", json={
            "email": otp_email,
            "full_name": "Test OTP User",
        })
        assert send_res.status_code == 200
        data = send_res.json()
        assert data["success"] is True
        assert "masked_email" in data
        assert data["dev_otp"] is not None
        assert len(data["dev_otp"]) == 6
        assert data["dev_otp"].isdigit()
        
        mock_send.assert_called_once()
        called_args = mock_send.call_args[0]
        assert called_args[0] == otp_email
        assert called_args[1] == data["dev_otp"]
        
        real_otp = data["dev_otp"]
        
        # 2. Enter invalid OTP -> Fails with attempts decrement
        bad_res = client.post("/api/auth/verify-otp", json={
            "email": otp_email,
            "otp": "000000" if real_otp != "000000" else "999999",
        })
        assert bad_res.status_code == 400
        assert "Invalid verification code" in bad_res.json()["detail"]
        assert "attempts remaining" in bad_res.json()["detail"]
        
        # 3. Enter valid OTP -> Succeeds with JWT token
        good_res = client.post("/api/auth/verify-otp", json={
            "email": otp_email,
            "otp": real_otp,
        })
        assert good_res.status_code == 200
        good_data = good_res.json()
        assert "access_token" in good_data
        assert good_data["user"]["email"] == otp_email
        assert good_data["user"]["is_verified"] is True
        
        # 4. Verify user in database is marked verified and token is cleared
        db = SessionLocal()
        db_user = db.query(User).filter(User.email == otp_email).first()
        assert db_user is not None
        assert db_user.is_verified is True
        assert db_user.verification_token is None
        assert db_user.otp_attempts == 0
        db.close()


def test_verify_otp_max_attempts_lockout():
    lockout_email = f"lockout_{uuid.uuid4().hex[:8]}@example.com"
    
    with patch("backend.routers.auth.send_verification_email") as mock_send:
        mock_send.return_value = {"success": True, "provider": "development_fallback"}
        res = client.post("/api/auth/send-otp", json={"email": lockout_email})
        assert res.status_code == 200
        
        # Attempt 5 incorrect OTPs
        for i in range(5):
            res_bad = client.post("/api/auth/verify-otp", json={
                "email": lockout_email,
                "otp": "111111",
            })
            assert res_bad.status_code == 400

        # 6th attempt should be blocked with 429
        res_blocked = client.post("/api/auth/verify-otp", json={
            "email": lockout_email,
            "otp": "111111",
        })
        assert res_blocked.status_code == 429
        assert "Too many failed" in res_blocked.json()["detail"]


def test_verify_otp_expired():
    expired_email = f"expired_{uuid.uuid4().hex[:8]}@example.com"
    
    with patch("backend.routers.auth.send_verification_email") as mock_send:
        mock_send.return_value = {"success": True, "provider": "development_fallback"}
        res = client.post("/api/auth/send-otp", json={"email": expired_email})
        assert res.status_code == 200
        
        # Manually expire the token in database
        db = SessionLocal()
        user = db.query(User).filter(User.email == expired_email).first()
        real_token = user.verification_token
        user.verification_token_expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()
        db.close()
        
        res_exp = client.post("/api/auth/verify-otp", json={
            "email": expired_email,
            "otp": real_token,
        })
        assert res_exp.status_code == 400
        assert "expired" in res_exp.json()["detail"].lower()


def test_verify_smtp_connection_missing_credentials():
    with patch("backend.email_service.SMTP_HOST", "smtp.gmail.com"), \
         patch("backend.email_service.SMTP_USER", ""), \
         patch("backend.email_service.SMTP_PASSWORD", ""):
        res = verify_smtp_connection()
        assert res["success"] is False
        assert res["code"] == "MISSING_CREDENTIALS"
        assert "SMTP_USER" in res["missing_variables"]


def test_verify_smtp_connection_success():
    mock_server = MagicMock()
    with patch("backend.email_service.SMTP_HOST", "smtp.gmail.com"), \
         patch("backend.email_service.SMTP_PORT", 465), \
         patch("backend.email_service.SMTP_USER", "sender@gmail.com"), \
         patch("backend.email_service.SMTP_PASSWORD", "abcd efgh ijkl mnop"), \
         patch("smtplib.SMTP_SSL", return_value=mock_server) as mock_ssl:
        res = verify_smtp_connection()
        assert res["success"] is True
        assert res["code"] == "OK"
        mock_ssl.assert_called_once_with("smtp.gmail.com", 465, timeout=10)
        # Spaces automatically cleaned from Google App Password
        mock_server.login.assert_called_once_with("sender@gmail.com", "abcdefghijklmnop")
        mock_server.quit.assert_called_once()


def test_verify_smtp_endpoint():
    with patch("backend.email_service.verify_smtp_connection") as mock_v:
        mock_v.return_value = {"success": True, "code": "OK", "message": "SMTP ready"}
        res = client.get("/api/auth/verify-smtp")
        assert res.status_code == 200
        assert res.json()["code"] == "OK"


def test_send_otp_smtp_not_configured_raises_500_and_no_false_success():
    """Verify that when real email delivery fails, HTTP 500 is returned rather than false success."""
    unconf_email = f"fail_{uuid.uuid4().hex[:8]}@example.com"
    with patch("backend.routers.auth.send_verification_email") as mock_send:
        mock_send.return_value = {
            "success": False,
            "code": "SMTP_NOT_CONFIGURED",
            "message": "Missing SMTP credentials"
        }
        res = client.post("/api/auth/send-otp", json={"email": unconf_email})
        assert res.status_code == 500
        assert "Unable to send verification code" in res.json()["detail"]

