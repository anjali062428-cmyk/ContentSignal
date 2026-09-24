"""
Backend Configuration.
"""
import os
from pathlib import Path
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


# JWT Configuration
_jwt_env = os.getenv("JWT_SECRET")
if APP_ENV == "production":
    if not _jwt_env or "change-in-production" in _jwt_env.lower():
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: JWT_SECRET environment variable must be set in production mode. "
            "Refusing to start with default or insecure secret."
        )
    JWT_SECRET = _jwt_env
else:
    JWT_SECRET = _jwt_env or "contentsignal-local-dev-jwt-secret-not-for-production"

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60 * 24  # 24 hours

# Development OTP Mode: Default false. When false, OTP is NEVER returned in API or shown in UI.
DEV_OTP_MODE = os.getenv("DEV_OTP_MODE", "false").lower() in ("true", "1", "yes")

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

# Sender Identity
EMAIL_FROM = (
    os.getenv("SMTP_FROM") or 
    os.getenv("EMAIL_FROM") or 
    os.getenv("SMTP_USER") or 
    os.getenv("EMAIL_USER") or 
    "noreply@contentsignal.ai"
).strip()
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "ContentSignal")

