"""
Email Delivery Service for ContentSignal.
Provides a clean provider abstraction:
EmailProvider
├── SMTPProvider
├── ResendProvider
└── NullEmailProvider

Features:
- Explicit provider selection (EMAIL_PROVIDER=smtp or EMAIL_PROVIDER=resend).
- No silent fallback between providers.
- Real delivery verification.
- Safe diagnostic test-email endpoint.
"""
from abc import ABC, abstractmethod
import logging
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid, formatdate
from typing import Dict, Any, Optional
import httpx

from backend.config import (
    RESEND_API_KEY as _CFG_RESEND_KEY,
    SMTP_HOST as _CFG_SMTP_HOST,
    SMTP_PORT as _CFG_SMTP_PORT,
    SMTP_USER as _CFG_SMTP_USER,
    SMTP_PASSWORD as _CFG_SMTP_PASS,
    SMTP_USE_TLS as _CFG_USE_TLS,
    SMTP_USE_SSL as _CFG_USE_SSL,
    EMAIL_FROM as _CFG_EMAIL_FROM,
    EMAIL_FROM_NAME as _CFG_FROM_NAME,
    APP_ENV as _CFG_APP_ENV,
    DEV_OTP_MODE as _CFG_DEV_OTP_MODE,
    EMAIL_PROVIDER as _CFG_EMAIL_PROVIDER,
    get_effective_email_from,
)

try:
    from backend.sms_service import get_sms_provider_status
except ImportError:
    def get_sms_provider_status():
        return {"provider": "unconfigured", "is_configured": False}

# Module-level variables for test patch compatibility
RESEND_API_KEY = _CFG_RESEND_KEY
SMTP_HOST = _CFG_SMTP_HOST
SMTP_PORT = _CFG_SMTP_PORT
SMTP_USER = _CFG_SMTP_USER
SMTP_PASSWORD = _CFG_SMTP_PASS
SMTP_USE_TLS = _CFG_USE_TLS
SMTP_USE_SSL = _CFG_USE_SSL
EMAIL_FROM = _CFG_EMAIL_FROM
EMAIL_FROM_NAME = _CFG_FROM_NAME
APP_ENV = _CFG_APP_ENV
DEV_OTP_MODE = _CFG_DEV_OTP_MODE
EMAIL_PROVIDER = _CFG_EMAIL_PROVIDER

logger = logging.getLogger("contentsignal.email")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def mask_email_address(email: str) -> str:
    """Mask email for privacy and secure logging."""
    if not email or "@" not in email:
        return email or ""
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


def _build_email_content(to_email: str, verification_code: str, full_name: Optional[str] = None) -> Dict[str, str]:
    """Construct plain-text and HTML verification email templates."""
    greeting_name = full_name.strip() if full_name and full_name.strip() else "there"
    subject = f"Your ContentSignal Verification Code: {verification_code}"
    
    text_content = f"""Hello {greeting_name},

Thank you for signing up for ContentSignal.

Your 6-digit confirmation code is:

{verification_code}

This code will expire in 10 minutes. Enter this code on the verification screen to activate your account.

If you did not request this code, please ignore this email.

Best regards,
The ContentSignal Team
"""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ContentSignal Verification Code</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b1120; color: #e2e8f0;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0b1120; padding: 40px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 520px; background-color: #111c34; border: 1px solid #1e293b; border-radius: 16px; overflow: hidden; padding: 32px 28px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
          <tr>
            <td align="center" style="padding-bottom: 24px;">
              <span style="font-size: 22px; font-weight: 800; letter-spacing: -0.5px; color: #ffffff;">
                Content<span style="color: #14b8a6;">Signal</span>
              </span>
              <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #2dd4bf; margin-top: 4px;">
                Decision Support Platform
              </div>
            </td>
          </tr>
          <tr>
            <td style="color: #cbd5e1; font-size: 15px; line-height: 24px;">
              <p style="margin-top: 0; color: #ffffff; font-size: 18px; font-weight: 700;">
                Confirm your email address
              </p>
              <p style="margin: 0 0 16px 0;">
                Hello {greeting_name},
              </p>
              <p style="margin: 0 0 24px 0;">
                Please use the 6-digit confirmation code below to complete your registration and activate your ContentSignal account:
              </p>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding: 12px 0 24px 0;">
              <div style="display: inline-block; background: #0f172a; border: 1px solid #0d9488; border-radius: 12px; padding: 16px 36px; text-align: center;">
                <span style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #2dd4bf;">
                  {verification_code}
                </span>
              </div>
            </td>
          </tr>
          <tr>
            <td style="color: #94a3b8; font-size: 13px; line-height: 20px; text-align: center; border-top: 1px solid #1e293b; padding-top: 20px;">
              <p style="margin: 0 0 8px 0;">
                This code will expire in <strong>10 minutes</strong>.
              </p>
              <p style="margin: 0;">
                If you did not request this email, no action is needed and you can safely ignore it.
              </p>
            </td>
          </tr>
        </table>
        <table role="presentation" width="100%" style="max-width: 520px; margin-top: 20px;">
          <tr>
            <td align="center" style="color: #64748b; font-size: 12px;">
              &copy; ContentSignal &bull; Content Intelligence &amp; Decision Support
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    return {"subject": subject, "text": text_content, "html": html_content}


# =========================================================================
# Email Provider Abstraction (Phase 8)
# =========================================================================

class BaseEmailProvider(ABC):
    @abstractmethod
    def send(self, to_email: str, subject: str, html: str, text: str) -> Dict[str, Any]:
        """Dispatch email and return structured delivery status."""
        pass


class ResendProvider(BaseEmailProvider):
    def send(self, to_email: str, subject: str, html: str, text: str) -> Dict[str, Any]:
        resend_key = sys.modules[__name__].RESEND_API_KEY
        if not resend_key:
            return {
                "success": False,
                "provider": "resend",
                "code": "RESEND_NOT_CONFIGURED",
                "delivery_id": None,
                "message": "RESEND_API_KEY is not configured.",
            }

        effective_from = get_effective_email_from("resend")
        from_name = sys.modules[__name__].EMAIL_FROM_NAME
        sender = f"{from_name} <{effective_from}>" if from_name else effective_from
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {resend_key.strip()}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "html": html,
            "text": text,
        }

        logger.info("[RESEND] Sending email to %s via %s", mask_email_address(to_email), effective_from)
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, headers=headers, json=payload)
                if response.status_code in (200, 201):
                    data = response.json()
                    delivery_id = data.get("id", "resend_ok")
                    logger.info("[RESEND] Delivery SUCCESS to %s (id: %s)", mask_email_address(to_email), delivery_id)
                    return {
                        "success": True,
                        "provider": "resend",
                        "delivery_id": delivery_id,
                        "message": "Verification email dispatched via Resend.",
                    }
                else:
                    err_detail = response.text[:200]
                    if response.status_code == 403 and ("testing email" in err_detail.lower() or "verify" in err_detail.lower() or "domain" in err_detail.lower()):
                        logger.error(
                            "[RESEND] 403 Domain Restriction: Test sender 'onboarding@resend.dev' can only deliver to the account owner's email address. To send to any recipient, verify your custom domain at https://resend.com/domains, or use Gmail SMTP."
                        )
                    else:
                        logger.error("[RESEND] API rejected dispatch to %s (HTTP %s): %s", mask_email_address(to_email), response.status_code, err_detail)
                    return {
                        "success": False,
                        "provider": "resend",
                        "code": f"RESEND_{response.status_code}",
                        "delivery_id": None,
                        "message": f"Resend API error: HTTP {response.status_code} - {err_detail}",
                    }
        except Exception as e:
            logger.error("[RESEND] Network exception during email dispatch to %s: %s", mask_email_address(to_email), type(e).__name__)
            return {
                "success": False,
                "provider": "resend",
                "code": "RESEND_NETWORK_ERROR",
                "delivery_id": None,
                "message": f"Network error connecting to Resend: {str(e)}",
            }


class SMTPProvider(BaseEmailProvider):
    def send(self, to_email: str, subject: str, html: str, text: str) -> Dict[str, Any]:
        smtp_host = sys.modules[__name__].SMTP_HOST
        smtp_port = sys.modules[__name__].SMTP_PORT
        smtp_user = sys.modules[__name__].SMTP_USER
        smtp_pass = sys.modules[__name__].SMTP_PASSWORD
        smtp_use_ssl = sys.modules[__name__].SMTP_USE_SSL
        smtp_use_tls = sys.modules[__name__].SMTP_USE_TLS
        from_name = sys.modules[__name__].EMAIL_FROM_NAME

        if not smtp_host:
            return {
                "success": False,
                "provider": "smtp",
                "code": "SMTP_NOT_CONFIGURED",
                "delivery_id": None,
                "stage": "preflight",
                "message": "SMTP_HOST is not configured in environment.",
            }

        smtp_sender = getattr(sys.modules[__name__], "EMAIL_FROM", "") or smtp_user
        effective_from = get_effective_email_from("smtp", custom_sender=smtp_sender)
        sender_header = f"{from_name} <{effective_from}>" if from_name else effective_from
        provider_msg_id = make_msgid(domain=effective_from.split("@")[-1] if "@" in effective_from else "contentsignal.ai")

        msg = MIMEMultipart("alternative")
        msg["From"] = sender_header
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = provider_msg_id
        msg.attach(MIMEText(text, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))

        server = None
        stage = "socket connect"
        try:
            use_ssl = (int(smtp_port) == 465) or (smtp_use_ssl and int(smtp_port) != 587)
            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_host.strip(), int(smtp_port), timeout=10)
            else:
                server = smtplib.SMTP(smtp_host.strip(), int(smtp_port), timeout=10)
                if smtp_use_tls:
                    stage = "starttls handshake"
                    server.starttls()

            if smtp_user and smtp_pass:
                stage = "authentication"
                clean_pw = smtp_pass.replace(" ", "") if "gmail.com" in smtp_host.lower() else smtp_pass
                server.login(smtp_user.strip(), clean_pw)
            elif not smtp_user or not smtp_pass:
                missing = []
                if not smtp_user: missing.append("SMTP_USER")
                if not smtp_pass: missing.append("SMTP_PASS")
                return {
                    "success": False,
                    "provider": "smtp",
                    "code": "MISSING_CREDENTIALS",
                    "delivery_id": None,
                    "stage": "authentication",
                    "message": f"Email delivery failed: Missing required credentials ({', '.join(missing)}).",
                }

            stage = "sendmail delivery"
            server.sendmail(effective_from, [to_email], msg.as_string())
            stage = "server quit"
            server.quit()
            server = None

            logger.info("[EMAIL] transporter: SUCCESS")
            logger.info("[EMAIL] send: SUCCESS")
            logger.info("[EMAIL] provider message ID: %s", provider_msg_id)
            return {
                "success": True,
                "provider": "smtp",
                "delivery_id": provider_msg_id,
                "message": "Verification email accepted by SMTP server.",
            }
        except smtplib.SMTPAuthenticationError as e:
            err_text = e.smtp_error.decode(errors="ignore") if isinstance(e.smtp_error, bytes) else str(e)
            logger.error("[EMAIL] send: FAILED. SMTP Authentication failed for %s", mask_email_address(to_email))
            return {
                "success": False,
                "provider": "smtp",
                "code": "EAUTH",
                "delivery_id": None,
                "stage": "authentication",
                "message": f"SMTP Authentication failed (check Google App Password): {err_text}",
            }
        except (smtplib.SMTPConnectError, TimeoutError, ConnectionRefusedError, OSError) as e:
            logger.error("[EMAIL] send: FAILED. Connection failed to %s:%s - %s", smtp_host, smtp_port, type(e).__name__)
            return {
                "success": False,
                "provider": "smtp",
                "code": "ECONNECTION",
                "delivery_id": None,
                "stage": "connection",
                "message": f"SMTP Connection failed to {smtp_host}:{smtp_port}: {str(e)}",
            }
        except Exception as e:
            logger.error("[EMAIL] send: FAILED at stage '%s': %s", stage, str(e))
            return {
                "success": False,
                "provider": "smtp",
                "code": type(e).__name__,
                "delivery_id": None,
                "stage": stage,
                "message": f"SMTP delivery error ({stage}): {str(e)}",
            }
        finally:
            if server:
                try:
                    server.close()
                except Exception:
                    pass


class NullEmailProvider(BaseEmailProvider):
    def send(self, to_email: str, subject: str, html: str, text: str) -> Dict[str, Any]:
        dev_mode = sys.modules[__name__].DEV_OTP_MODE
        app_env = sys.modules[__name__].APP_ENV
        if dev_mode or app_env == "development":
            return {
                "success": True,
                "provider": "development_fallback",
                "delivery_id": "dev_simulated",
                "message": "Development fallback simulated email delivery.",
            }
        return {
            "success": False,
            "provider": "unconfigured",
            "code": "EMAIL_NOT_CONFIGURED",
            "delivery_id": None,
            "message": "No email provider is configured. Please configure SMTP or Resend credentials.",
        }


# =========================================================================
# Factory and Entrypoints
# =========================================================================

def get_email_provider() -> str:
    """
    Determine the active email provider based on strict priority:
    1. Explicit EMAIL_PROVIDER=smtp -> ALWAYS use smtp.
    2. Explicit EMAIL_PROVIDER=resend -> ALWAYS use resend.
    3. If EMAIL_PROVIDER is missing or empty -> Auto-detect:
       - Resend if RESEND_API_KEY present
       - SMTP if SMTP_HOST present
       - Development fallback if dev mode or local environment
       - Unconfigured otherwise
    """
    provider_pref = getattr(sys.modules[__name__], "EMAIL_PROVIDER", "").strip().lower()
    resend_key = getattr(sys.modules[__name__], "RESEND_API_KEY", "").strip()
    smtp_host = getattr(sys.modules[__name__], "SMTP_HOST", "").strip()
    dev_mode = getattr(sys.modules[__name__], "DEV_OTP_MODE", False)
    app_env = getattr(sys.modules[__name__], "APP_ENV", "development").lower()

    # Priority 1 & 2: Explicit provider choice ALWAYS wins. No silent fallback!
    if provider_pref == "smtp":
        return "smtp"
    if provider_pref == "resend":
        return "resend"

    # Priority 3: Auto-detection only when EMAIL_PROVIDER is not explicitly specified
    if resend_key:
        return "resend"
    if smtp_host:
        return "smtp"
    if dev_mode or app_env == "development":
        return "development_fallback"
    return "unconfigured"


def get_email_provider_instance() -> BaseEmailProvider:
    """Return an instantiated EmailProvider based on current configuration."""
    provider = get_email_provider()
    if provider == "resend":
        return ResendProvider()
    if provider == "smtp":
        return SMTPProvider()
    return NullEmailProvider()


def get_email_provider_status() -> Dict[str, Any]:
    """Return non-sensitive status information about email and SMS configuration."""
    provider = get_email_provider()
    
    if provider == "smtp":
        smtp_sender = getattr(sys.modules[__name__], "EMAIL_FROM", "") or getattr(sys.modules[__name__], "SMTP_USER", "")
        effective_from = get_effective_email_from("smtp", custom_sender=smtp_sender)
    else:
        resend_sender = getattr(sys.modules[__name__], "EMAIL_FROM", "")
        effective_from = get_effective_email_from("resend", custom_sender=resend_sender)

    from_name = getattr(sys.modules[__name__], "EMAIL_FROM_NAME", "ContentSignal")
    sender = f"{from_name} <{effective_from}>" if from_name else effective_from

    smtp_host = getattr(sys.modules[__name__], "SMTP_HOST", "").strip()
    smtp_user = getattr(sys.modules[__name__], "SMTP_USER", "").strip()
    smtp_pass = getattr(sys.modules[__name__], "SMTP_PASSWORD", "").strip()
    resend_key = getattr(sys.modules[__name__], "RESEND_API_KEY", "").strip()

    if provider == "smtp":
        is_configured = bool(smtp_host and smtp_user and smtp_pass)
    elif provider == "resend":
        is_configured = bool(resend_key)
    elif provider == "development_fallback":
        is_configured = True
    else:
        is_configured = False

    return {
        "provider": provider,
        "is_configured": is_configured,
        "sender": sender,
        "environment": getattr(sys.modules[__name__], "APP_ENV", "development"),
        "smtp_host_configured": bool(smtp_host),
        "resend_configured": bool(resend_key),
        "sms": get_sms_provider_status(),
    }


def send_verification_email(
    to_email: str,
    verification_code: str,
    full_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Primary verification email entrypoint.
    Dispatches to the explicitly configured EmailProvider without cross-provider fallback.
    """
    content = _build_email_content(to_email, verification_code, full_name)
    provider_inst = get_email_provider_instance()
    return provider_inst.send(to_email, content["subject"], content["html"], content["text"])


def verify_smtp_connection() -> Dict[str, Any]:
    """Verify SMTP connection and authentication safely without leaking credentials."""
    smtp_host = getattr(sys.modules[__name__], "SMTP_HOST", "")
    smtp_port = getattr(sys.modules[__name__], "SMTP_PORT", 587)
    smtp_user = getattr(sys.modules[__name__], "SMTP_USER", "")
    smtp_pass = getattr(sys.modules[__name__], "SMTP_PASSWORD", "")
    smtp_use_ssl = getattr(sys.modules[__name__], "SMTP_USE_SSL", False)
    smtp_use_tls = getattr(sys.modules[__name__], "SMTP_USE_TLS", True)

    if not smtp_host:
        return {
            "success": False,
            "code": "SMTP_NOT_CONFIGURED",
            "message": "SMTP_HOST is not configured in .env",
            "missing_variables": ["SMTP_HOST", "SMTP_USER", "SMTP_PASS"],
        }

    missing = []
    if not smtp_user: missing.append("SMTP_USER")
    if not smtp_pass: missing.append("SMTP_PASSWORD")
    if missing:
        return {
            "success": False,
            "code": "MISSING_CREDENTIALS",
            "message": f"Missing required SMTP credentials: {', '.join(missing)}",
            "missing_variables": missing,
        }

    server = None
    try:
        use_ssl = (int(smtp_port) == 465) or (smtp_use_ssl and int(smtp_port) != 587)
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_host.strip(), int(smtp_port), timeout=10)
        else:
            server = smtplib.SMTP(smtp_host.strip(), int(smtp_port), timeout=10)
            if smtp_use_tls:
                server.starttls()

        clean_pw = smtp_pass.replace(" ", "") if "gmail.com" in smtp_host.lower() else smtp_pass
        server.login(smtp_user, clean_pw)
        server.quit()
        server = None
        return {
            "success": True,
            "code": "OK",
            "message": f"Successfully connected and authenticated with {smtp_host}:{smtp_port}.",
        }
    except Exception as e:
        return {
            "success": False,
            "code": type(e).__name__,
            "message": f"SMTP handshake failed: {str(e)}",
        }
    finally:
        if server:
            try:
                server.close()
            except Exception:
                pass


def test_send_email(to_email: str) -> Dict[str, Any]:
    """
    Phase 24: Diagnostic endpoint helper to test sending a real verification email.
    Never returns credentials or secrets.
    """
    test_otp = "123456"
    res = send_verification_email(to_email, test_otp, "Diagnostics Tester")
    return {
        "success": res.get("success", False),
        "provider": res.get("provider", "unknown"),
        "delivery_id": res.get("delivery_id"),
        "code": res.get("code", "OK" if res.get("success") else "DELIVERY_FAILED"),
        "message": res.get("message", "Test dispatch completed."),
    }
