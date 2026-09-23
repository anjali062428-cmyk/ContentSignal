"""
ContentSignal — SMTP Connection & Transporter Diagnostic Script.
Safely tests SMTP connection and authentication without leaking credentials.
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from backend.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_SECURE,
    SMTP_USE_SSL,
    SMTP_USE_TLS,
    SMTP_USER,
    SMTP_PASSWORD,
    EMAIL_FROM,
    DEV_OTP_MODE,
)
from backend.email_service import verify_smtp_connection, mask_email_address


def main():
    print("=" * 60)
    print("ContentSignal — SMTP Transporter Diagnostic")
    print("=" * 60)
    print(f"SMTP Host:       {SMTP_HOST or '(not configured)'}")
    print(f"SMTP Port:       {SMTP_PORT}")
    print(f"SMTP Secure:     {SMTP_SECURE}")
    print(f"SMTP SSL:        {SMTP_USE_SSL}")
    print(f"SMTP TLS:        {SMTP_USE_TLS}")
    print(f"SMTP User:       {mask_email_address(SMTP_USER) if SMTP_USER else '(not set)'}")
    print(f"SMTP Password:   {'[CONFIGURED - HIDDEN]' if SMTP_PASSWORD else '(not set)'}")
    print(f"Email From:      {EMAIL_FROM}")
    print(f"DEV_OTP_MODE:    {DEV_OTP_MODE}")
    print("-" * 60)

    result = verify_smtp_connection()

    if result.get("success"):
        print("\nSMTP connection = SUCCESS")
        print("Transporter is operational. Ready to dispatch real verification emails.")
        print(f"Provider: {result.get('host')}:{result.get('port')}")
        print(f"Sender:   {result.get('sender')}")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\nSMTP connection = FAILED")
        print(f"Error Code:    {result.get('code')}")
        print(f"Error Message: {result.get('message')}")
        if result.get("missing_variables"):
            print(f"Missing in .env: {', '.join(result.get('missing_variables'))}")
        print("-" * 60)
        print("GMAIL CONFIGURATION CHECKLIST:")
        print("1. Set SMTP_HOST=smtp.gmail.com in .env")
        print("2. Set SMTP_PORT=465 in .env")
        print("3. Set SMTP_SECURE=true in .env")
        print("4. Set SMTP_USER=<your_gmail> in .env")
        print("5. Set SMTP_PASS=<16_character_app_password> in .env")
        print("   (Generate at: https://myaccount.google.com/apppasswords)")
        print("6. Set SMTP_FROM=<your_gmail> in .env")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
