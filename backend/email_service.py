"""
Email Delivery Service for ContentSignal.
Supports Resend API, SMTP, and secure development fallback.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid, formatdate
from typing import Dict, Any, Optional
import httpx

from backend.config import (
    RESEND_API_KEY,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_USE_TLS,
    SMTP_USE_SSL,
    EMAIL_FROM,
    EMAIL_FROM_NAME,
    APP_ENV,
    DEV_OTP_MODE,
    get_effective_email_from,
)

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


def get_email_provider() -> str:
    """Determine the active email provider based on configuration."""
    if RESEND_API_KEY and RESEND_API_KEY.strip():
        return "resend"
    if SMTP_HOST and SMTP_HOST.strip():
        return "smtp"
    if DEV_OTP_MODE or APP_ENV == "development":
        return "development_fallback"
    return "unconfigured"


def get_email_provider_status() -> Dict[str, Any]:
    """Return non-sensitive status information about email configuration."""
    provider = get_email_provider()
    effective_from = get_effective_email_from(provider)
    sender = f"{EMAIL_FROM_NAME} <{effective_from}>" if EMAIL_FROM_NAME else effective_from
    return {
        "provider": provider,
        "is_configured": provider in ("resend", "smtp"),
        "sender": sender,
        "environment": APP_ENV,
        "smtp_host_configured": bool(SMTP_HOST),
        "resend_configured": bool(RESEND_API_KEY),
    }


def verify_smtp_connection() -> Dict[str, Any]:
    """
    Verify SMTP connection and authentication without leaking credentials.
    Emits standardized safe log messages:
      [EMAIL] transporter: SUCCESS
    or:
      [EMAIL] transporter: FAILED
      [EMAIL] error code: <safe code>
      [EMAIL] error message: <safe message>
    """
    if not SMTP_HOST:
        logger.error("[EMAIL] transporter: FAILED")
        logger.error("[EMAIL] error code: SMTP_NOT_CONFIGURED")
        logger.error("[EMAIL] error message: SMTP_HOST is not set in environment (.env).")
        return {
            "success": False,
            "code": "SMTP_NOT_CONFIGURED",
            "message": "SMTP_HOST is not configured in .env",
            "missing_variables": ["SMTP_HOST", "SMTP_USER", "SMTP_PASS"],
        }

    missing = []
    if not SMTP_USER:
        missing.append("SMTP_USER")
    if not SMTP_PASSWORD:
        missing.append("SMTP_PASS")
    if missing:
        logger.error("[EMAIL] transporter: FAILED")
        logger.error("[EMAIL] error code: MISSING_CREDENTIALS")
        logger.error("[EMAIL] error message: Missing required SMTP credentials: %s", ", ".join(missing))
        return {
            "success": False,
            "code": "MISSING_CREDENTIALS",
            "message": f"Missing required SMTP credentials: {', '.join(missing)}",
            "missing_variables": missing,
        }

    logger.info(
        "[EMAIL] Testing SMTP connection to %s:%s (SSL=%s, TLS=%s)...",
        SMTP_HOST,
        SMTP_PORT,
        SMTP_USE_SSL,
        SMTP_USE_TLS,
    )
    server = None
    try:
        use_ssl = (int(SMTP_PORT) == 465) or (SMTP_USE_SSL and int(SMTP_PORT) != 587)
        if use_ssl:
            server = smtplib.SMTP_SSL(SMTP_HOST.strip(), int(SMTP_PORT), timeout=10)
        else:
            server = smtplib.SMTP(SMTP_HOST.strip(), int(SMTP_PORT), timeout=10)
            if SMTP_USE_TLS:
                server.starttls()

        clean_pw = SMTP_PASSWORD
        if "gmail.com" in SMTP_HOST.lower():
            clean_pw = clean_pw.replace(" ", "")

        server.login(SMTP_USER, clean_pw)
        server.quit()
        server = None
        logger.info("[EMAIL] transporter: SUCCESS")
        return {
            "success": True,
            "code": "OK",
            "message": "SMTP transporter connection and authentication verified successfully.",
            "host": SMTP_HOST,
            "port": SMTP_PORT,
            "secure": SMTP_USE_SSL,
            "sender": mask_email_address(SMTP_USER),
        }
    except smtplib.SMTPAuthenticationError as e:
        err_text = e.smtp_error.decode(errors="ignore") if isinstance(e.smtp_error, bytes) else str(e)
        logger.error("[EMAIL] transporter: FAILED")
        logger.error("[EMAIL] error code: EAUTH (535)")
        logger.error("[EMAIL] error message: Authentication failed for sender. Check SMTP_USER and Google App Password.")
        return {
            "success": False,
            "code": "EAUTH",
            "message": f"SMTP Authentication failed (Check SMTP_USER and Google App Password): {err_text}",
        }
    except (smtplib.SMTPConnectError, TimeoutError, ConnectionRefusedError, OSError) as e:
        logger.error("[EMAIL] transporter: FAILED")
        logger.error("[EMAIL] error code: ECONNECTION")
        logger.error("[EMAIL] error message: Connection failed to %s:%s - %s", SMTP_HOST, SMTP_PORT, type(e).__name__)
        return {
            "success": False,
            "code": "ECONNECTION",
            "message": f"Failed to connect to SMTP server at {SMTP_HOST}:{SMTP_PORT} ({type(e).__name__})",
        }
    except Exception as e:
        logger.error("[EMAIL] transporter: FAILED")
        logger.error("[EMAIL] error code: %s", type(e).__name__)
        logger.error("[EMAIL] error message: %s", str(e))
        return {
            "success": False,
            "code": type(e).__name__,
            "message": f"SMTP verification error: {str(e)}",
        }
    finally:
        if server:
            try:
                server.close()
            except Exception:
                pass


def _build_email_content(to_email: str, verification_code: str, full_name: Optional[str] = None) -> Dict[str, str]:
    """Construct plain-text and HTML verification email templates."""
    greeting_name = full_name.strip() if full_name and full_name.strip() else "there"
    
    subject = f"Your ContentSignal Verification Code: {verification_code}"
    
    text_content = f"""Hello {greeting_name},

Thank you for signing up for ContentSignal.

Your 6-digit confirmation code is:

{verification_code}

This code will expire in 24 hours. Enter this code on the verification screen to activate your account.

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
                This code will expire in <strong>24 hours</strong>.
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
    return {
        "subject": subject,
        "text": text_content,
        "html": html_content,
    }


def _send_via_resend(to_email: str, subject: str, html: str, text: str) -> Dict[str, Any]:
    """Send verification email using Resend HTTP API."""
    effective_from = get_effective_email_from("resend")
    sender = f"{EMAIL_FROM_NAME} <{effective_from}>" if EMAIL_FROM_NAME else effective_from
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "html": html,
        "text": text,
    }

    sender_domain = effective_from.split("@")[-1] if "@" in effective_from else "unknown"
    logger.info("[RESEND] Sending email to %s via @%s", mask_email_address(to_email), sender_domain)

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)
            if response.status_code in (200, 201):
                data = response.json()
                delivery_id = data.get("id", "resend_ok")
                logger.info(
                    "[RESEND] Delivery SUCCESS to %s (id: %s)",
                    mask_email_address(to_email),
                    delivery_id,
                )
                return {
                    "success": True,
                    "provider": "resend",
                    "delivery_id": delivery_id,
                    "message": "Verification email dispatched via Resend.",
                }
            else:
                err_detail = response.text[:200]
                logger.error(
                    "[RESEND] API rejected dispatch to %s (HTTP %s): %s",
                    mask_email_address(to_email),
                    response.status_code,
                    err_detail,
                )
                return {
                    "success": False,
                    "provider": "resend",
                    "code": f"RESEND_{response.status_code}",
                    "delivery_id": None,
                    "message": f"Resend API error: HTTP {response.status_code}",
                }
    except Exception as e:
        logger.error(
            "[RESEND] Network exception during email dispatch to %s: %s",
            mask_email_address(to_email),
            type(e).__name__,
        )
        return {
            "success": False,
            "provider": "resend",
            "code": "RESEND_NETWORK_ERROR",
            "delivery_id": None,
            "message": "Network exception during email dispatch.",
        }


def _send_via_smtp(to_email: str, subject: str, html: str, text: str) -> Dict[str, Any]:
    """Send verification email using authenticated SMTP (e.g. Gmail)."""
    if not SMTP_HOST:
        logger.error("[EMAIL] send: FAILED")
        logger.error("[EMAIL] error code: SMTP_NOT_CONFIGURED")
        logger.error("[EMAIL] error message: SMTP_HOST is not set in environment.")
        return {
            "success": False,
            "code": "SMTP_NOT_CONFIGURED",
            "provider": "smtp",
            "delivery_id": None,
            "message": "Email delivery service is not configured. Missing SMTP_HOST in environment.",
            "missing_variables": ["SMTP_HOST", "SMTP_USER", "SMTP_PASS"],
        }

    # When using authenticated SMTP (like Gmail), envelope sender must match the authenticated user
    effective_from = (
        SMTP_USER.strip()
        if (SMTP_USER and "@" in SMTP_USER)
        else (EMAIL_FROM.strip() if EMAIL_FROM else "noreply@contentsignal.ai")
    )
    sender = f"{EMAIL_FROM_NAME} <{effective_from}>" if EMAIL_FROM_NAME else effective_from
    
    # Generate RFC 2822 Message-ID
    domain = SMTP_HOST.split(".")[-2] + "." + SMTP_HOST.split(".")[-1] if "." in SMTP_HOST else "contentsignal.ai"
    provider_msg_id = make_msgid(domain=domain)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = provider_msg_id
    
    part_text = MIMEText(text, "plain", "utf-8")
    part_html = MIMEText(html, "html", "utf-8")
    msg.attach(part_text)
    msg.attach(part_html)

    server = None
    stage = "initialization"
    try:
        stage = f"connecting to {SMTP_HOST}:{SMTP_PORT}"
        use_ssl = (int(SMTP_PORT) == 465) or (SMTP_USE_SSL and int(SMTP_PORT) != 587)
        if use_ssl:
            server = smtplib.SMTP_SSL(SMTP_HOST.strip(), int(SMTP_PORT), timeout=10)
        else:
            server = smtplib.SMTP(SMTP_HOST.strip(), int(SMTP_PORT), timeout=10)
            if SMTP_USE_TLS:
                stage = "STARTTLS negotiation"
                server.starttls()

        if SMTP_USER and SMTP_PASSWORD:
            stage = "SMTP authentication"
            clean_pw = SMTP_PASSWORD.strip()
            if "gmail.com" in (SMTP_HOST or "").lower():
                clean_pw = clean_pw.replace(" ", "")
            server.login(SMTP_USER.strip(), clean_pw)
        else:
            missing = []
            if not SMTP_USER:
                missing.append("SMTP_USER")
            if not SMTP_PASSWORD:
                missing.append("SMTP_PASS")
            logger.error("[EMAIL] send: FAILED")
            logger.error("[EMAIL] error code: MISSING_CREDENTIALS")
            logger.error("[EMAIL] error message: Missing required SMTP credentials: %s", ", ".join(missing))
            if server:
                server.quit()
            return {
                "success": False,
                "provider": "smtp",
                "code": "MISSING_CREDENTIALS",
                "delivery_id": None,
                "stage": "authentication",
                "message": f"Email delivery failed: Missing required credentials ({', '.join(missing)}).",
                "missing_variables": missing,
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
        logger.error("[EMAIL] send: FAILED")
        logger.error("[EMAIL] error code: EAUTH (535)")
        logger.error("[EMAIL] error message: SMTP Authentication failed for %s. Check Google App Password.", mask_email_address(to_email))
        return {
            "success": False,
            "provider": "smtp",
            "code": "EAUTH",
            "delivery_id": None,
            "stage": "authentication",
            "message": f"SMTP Authentication failed (check username and Google App Password): {err_text}",
        }
    except smtplib.SMTPRecipientsRefused as e:
        logger.error("[EMAIL] send: FAILED")
        logger.error("[EMAIL] error code: ERECIPIENT")
        logger.error("[EMAIL] error message: Recipient address %s rejected by server.", mask_email_address(to_email))
        return {
            "success": False,
            "provider": "smtp",
            "code": "ERECIPIENT",
            "delivery_id": None,
            "stage": "recipients",
            "message": f"Recipient address rejected by SMTP provider: {mask_email_address(to_email)}",
        }
    except (smtplib.SMTPConnectError, TimeoutError, ConnectionRefusedError, OSError) as e:
        logger.error("[EMAIL] send: FAILED")
        logger.error("[EMAIL] error code: ECONNECTION")
        logger.error("[EMAIL] error message: Connection failed to %s:%s - %s", SMTP_HOST, SMTP_PORT, type(e).__name__)
        return {
            "success": False,
            "provider": "smtp",
            "code": "ECONNECTION",
            "delivery_id": None,
            "stage": "connection",
            "message": f"SMTP Connection failed to {SMTP_HOST}:{SMTP_PORT}: {str(e)}",
        }
    except Exception as e:
        logger.error("[EMAIL] send: FAILED")
        logger.error("[EMAIL] error code: %s", type(e).__name__)
        logger.error("[EMAIL] error message: SMTP delivery failed at stage '%s': %s", stage, str(e))
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


def send_verification_email(
    to_email: str,
    verification_code: str,
    full_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Primary verification email entrypoint.
    Dispatches to Resend, SMTP, or secure development fallback based on configuration.
    """
    provider = get_email_provider()
    content = _build_email_content(to_email, verification_code, full_name)

    if provider == "resend":
        return _send_via_resend(to_email, content["subject"], content["html"], content["text"])

    if provider == "smtp":
        return _send_via_smtp(to_email, content["subject"], content["html"], content["text"])

    # Development Fallback: returns simulated delivery in development
    if provider == "development_fallback":
        logger.warning(
            "[DEV EMAIL FALLBACK] Email verification simulated for %s (code: %s).",
            mask_email_address(to_email),
            verification_code,
        )
        return {
            "success": True,
            "provider": "development_fallback",
            "delivery_id": "dev_simulated",
            "message": "Development fallback simulated email delivery.",
        }

    # When no provider is configured, delivery FAILS
    missing_vars = []
    if not SMTP_HOST:
        missing_vars.append("SMTP_HOST")
    if not SMTP_USER:
        missing_vars.append("SMTP_USER")
    if not SMTP_PASSWORD:
        missing_vars.append("SMTP_PASS")

    err_msg = (
        f"Email delivery service is not configured. Missing required environment variables: {', '.join(missing_vars)}. "
        "Please configure Gmail SMTP or Resend in .env."
    )
    logger.error("[EMAIL] send: FAILED")
    logger.error("[EMAIL] error code: SMTP_NOT_CONFIGURED")
    logger.error("[EMAIL] error message: %s", err_msg)

    return {
        "success": False,
        "code": "SMTP_NOT_CONFIGURED",
        "provider": "unconfigured",
        "delivery_id": None,
        "message": err_msg,
        "missing_variables": missing_vars,
    }

