"""
Backend Configuration.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/content_intelligence.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Application Environment
APP_ENV = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()

# Frontend URL for production CORS (e.g. https://contentsignal.vercel.app or comma-separated URLs)
FRONTEND_URL = (os.getenv("FRONTEND_URL") or "").strip()


# Clerk Authentication Configuration
CLERK_SECRET_KEY = (os.getenv("CLERK_SECRET_KEY") or "").strip()
CLERK_PUBLISHABLE_KEY = (
    os.getenv("CLERK_PUBLISHABLE_KEY") or 
    os.getenv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY") or 
    ""
).strip()
CLERK_JWT_KEY = (os.getenv("CLERK_JWT_KEY") or os.getenv("CLERK_PEM_PUBLIC_KEY") or "").strip()
CLERK_JWKS_URL = (os.getenv("CLERK_JWKS_URL") or "").strip()
CLERK_ISSUER = (os.getenv("CLERK_ISSUER") or "").strip()

# Legacy / Testing JWT Configuration
_jwt_env = os.getenv("JWT_SECRET")
JWT_SECRET = _jwt_env or "contentsignal-clerk-transition-jwt-secret"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60 * 24  # 24 hours

# Development OTP Mode: Default false. When false, OTP is NEVER returned in API or shown in UI.
DEV_OTP_MODE = os.getenv("DEV_OTP_MODE", "false").lower() in ("true", "1", "yes")

# Email Provider Preference: 'smtp', 'resend', or auto-detect
EMAIL_PROVIDER = (os.getenv("EMAIL_PROVIDER") or "").strip().lower()

# Email Provider Configuration: Resend API
RESEND_API_KEY = (os.getenv("RESEND_API_KEY") or "").strip()

# Email Provider Configuration: SMTP (Supports SMTP_*, EMAIL_*, and standard aliases)
SMTP_HOST = (os.getenv("SMTP_HOST") or os.getenv("EMAIL_HOST") or "").strip()
SMTP_SECURE = os.getenv("SMTP_SECURE", "false").lower() in ("true", "1", "yes")
_default_port = "465" if SMTP_SECURE else "587"
SMTP_PORT = int(os.getenv("SMTP_PORT") or os.getenv("EMAIL_PORT") or _default_port)
SMTP_USER = (os.getenv("SMTP_USER") or os.getenv("EMAIL_USER") or "").strip()
SMTP_PASSWORD = (
    os.getenv("SMTP_PASSWORD") or 
    os.getenv("SMTP_PASS") or 
    os.getenv("EMAIL_PASS") or 
    os.getenv("EMAIL_PASSWORD") or 
    ""
).strip()
SMTP_USE_SSL = SMTP_SECURE or os.getenv("SMTP_USE_SSL", "false").lower() in ("true", "1", "yes") or SMTP_PORT == 465
SMTP_USE_TLS = (os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")) and not SMTP_USE_SSL

# Sender Identity Configuration
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "ContentSignal").strip()
_raw_configured_from = (
    os.getenv("EMAIL_FROM") or 
    os.getenv("RESEND_FROM") or 
    os.getenv("SMTP_FROM") or 
    os.getenv("SMTP_USER") or 
    os.getenv("EMAIL_USER") or 
    ""
).strip()

PUBLIC_EMAIL_DOMAINS = ("gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com")

def get_effective_email_from(provider: str, custom_sender: Optional[str] = None) -> str:
    """
    Deterministic email sender resolution.
    If provider is Resend and the configured sender is a public webmail domain (e.g. gmail.com)
    which Resend strictly rejects with HTTP 403, safely use 'onboarding@resend.dev'.
    If a verified custom domain or custom address is provided, use that.
    For SMTP or local dev, return the configured sender.
    """
    raw_from = custom_sender or _raw_configured_from
    if not raw_from:
        raw_from = (
            os.getenv("EMAIL_FROM") or 
            os.getenv("SMTP_FROM") or 
            os.getenv("SMTP_USER") or 
            os.getenv("RESEND_FROM") or 
            os.getenv("EMAIL_USER") or 
            ""
        ).strip()

    raw_clean = raw_from.strip()
    if "<" in raw_clean and ">" in raw_clean:
        import re
        match = re.search(r"<([^>]+)>", raw_clean)
        if match:
            raw_clean = match.group(1).strip()

    if provider == "resend":
        if raw_clean and "@" in raw_clean:
            domain = raw_clean.split("@")[-1].strip().lower()
            if domain in PUBLIC_EMAIL_DOMAINS:
                return "onboarding@resend.dev"
            return raw_clean
        return "onboarding@resend.dev"

    return raw_clean or "noreply@contentsignal.ai"

def _determine_initial_provider() -> str:
    pref = EMAIL_PROVIDER.strip().lower()
    if pref in ("smtp", "resend"):
        return pref
    if RESEND_API_KEY:
        return "resend"
    if SMTP_HOST:
        return "smtp"
    return "smtp"

EMAIL_FROM = get_effective_email_from(_determine_initial_provider())

# =========================================================================
# SMS Provider Configuration (Architecture Ready for Twilio / MSG91)
# =========================================================================
SMS_PROVIDER = (os.getenv("SMS_PROVIDER") or "").strip().lower()

# Twilio SMS
TWILIO_ACCOUNT_SID = (os.getenv("TWILIO_ACCOUNT_SID") or "").strip()
TWILIO_AUTH_TOKEN = (os.getenv("TWILIO_AUTH_TOKEN") or "").strip()
TWILIO_FROM_NUMBER = (os.getenv("TWILIO_FROM_NUMBER") or os.getenv("TWILIO_PHONE_NUMBER") or "").strip()

# MSG91 (India DLT Compliant SMS)
MSG91_AUTH_KEY = (os.getenv("MSG91_AUTH_KEY") or "").strip()
MSG91_SENDER_ID = (os.getenv("MSG91_SENDER_ID") or "").strip()
MSG91_TEMPLATE_ID = (os.getenv("MSG91_TEMPLATE_ID") or "").strip()

