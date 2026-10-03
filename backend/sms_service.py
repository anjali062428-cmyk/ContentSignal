"""
SMS Delivery Service for ContentSignal.
Provides a clean provider abstraction:
SMSProvider
├── TwilioSMSProvider
├── MSG91SMSProvider
└── NullSMSProvider

Strict Requirements:
- Architecture-ready for Twilio and MSG91 (India DLT Compliant).
- NEVER fakes SMS delivery if unconfigured.
- Truthfully returns 'SMS_NOT_CONFIGURED' and clear user-facing guidance.
- Mobile verification is decoupled so email verification remains functional independently.
"""
from abc import ABC, abstractmethod
import logging
import sys
from typing import Dict, Any, Optional
import httpx

from backend.config import (
    SMS_PROVIDER as _CFG_SMS_PROVIDER,
    TWILIO_ACCOUNT_SID as _CFG_TWILIO_SID,
    TWILIO_AUTH_TOKEN as _CFG_TWILIO_TOKEN,
    TWILIO_FROM_NUMBER as _CFG_TWILIO_NUM,
    MSG91_AUTH_KEY as _CFG_MSG91_KEY,
    MSG91_SENDER_ID as _CFG_MSG91_SENDER,
    MSG91_TEMPLATE_ID as _CFG_MSG91_TEMPLATE,
    APP_ENV as _CFG_APP_ENV,
)

# Module-level variables for test mocking compatibility
SMS_PROVIDER = _CFG_SMS_PROVIDER
TWILIO_ACCOUNT_SID = _CFG_TWILIO_SID
TWILIO_AUTH_TOKEN = _CFG_TWILIO_TOKEN
TWILIO_FROM_NUMBER = _CFG_TWILIO_NUM
MSG91_AUTH_KEY = _CFG_MSG91_KEY
MSG91_SENDER_ID = _CFG_MSG91_SENDER
MSG91_TEMPLATE_ID = _CFG_MSG91_TEMPLATE
APP_ENV = _CFG_APP_ENV

logger = logging.getLogger("contentsignal.sms")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def mask_mobile_number(mobile: str) -> str:
    """Mask mobile number for privacy and safe logging (e.g. +91 98****1234)."""
    if not mobile:
        return ""
    clean = mobile.strip()
    if len(clean) <= 4:
        return "****"
    return clean[:3] + "*" * (len(clean) - 6) + clean[-3:] if len(clean) >= 7 else clean[:2] + "****" + clean[-2:]


class BaseSMSProvider(ABC):
    @abstractmethod
    def send(self, to_mobile: str, otp: str, country_code: str = "+91") -> Dict[str, Any]:
        """Dispatch SMS OTP and return structured delivery status."""
        pass


class TwilioSMSProvider(BaseSMSProvider):
    def send(self, to_mobile: str, otp: str, country_code: str = "+91") -> Dict[str, Any]:
        sid = getattr(sys.modules[__name__], "TWILIO_ACCOUNT_SID", "")
        token = getattr(sys.modules[__name__], "TWILIO_AUTH_TOKEN", "")
        from_num = getattr(sys.modules[__name__], "TWILIO_FROM_NUMBER", "")

        if not (sid and token and from_num):
            return {
                "success": False,
                "provider": "twilio",
                "code": "TWILIO_MISSING_CREDENTIALS",
                "delivery_id": None,
                "message": "Missing required Twilio credentials in environment.",
            }

        formatted = to_mobile.strip()
        if country_code and not formatted.startswith("+"):
            c_code = country_code if country_code.startswith("+") else f"+{country_code}"
            formatted = f"{c_code}{formatted}"

        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        body_text = f"Your ContentSignal verification code is: {otp}. Valid for 5 minutes. Do not share this code."
        logger.info("[SMS] Sending SMS OTP to %s via Twilio", mask_mobile_number(formatted))

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    url,
                    data={"From": from_num, "To": formatted, "Body": body_text},
                    auth=(sid, token),
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    delivery_id = data.get("sid", "twilio_ok")
                    logger.info("[SMS] Twilio delivery SUCCESS (SID: %s)", delivery_id)
                    return {
                        "success": True,
                        "provider": "twilio",
                        "delivery_id": delivery_id,
                        "message": "SMS verification code sent via Twilio.",
                    }
                else:
                    err_msg = resp.text[:200]
                    logger.error("[SMS] Twilio rejected dispatch (HTTP %s): %s", resp.status_code, err_msg)
                    return {
                        "success": False,
                        "provider": "twilio",
                        "code": f"TWILIO_{resp.status_code}",
                        "delivery_id": None,
                        "message": f"Twilio API rejected delivery (HTTP {resp.status_code})",
                    }
        except Exception as e:
            logger.error("[SMS] Network exception during Twilio dispatch: %s", type(e).__name__)
            return {
                "success": False,
                "provider": "twilio",
                "code": "TWILIO_NETWORK_ERROR",
                "delivery_id": None,
                "message": "Network error during Twilio SMS dispatch.",
            }


class MSG91SMSProvider(BaseSMSProvider):
    def send(self, to_mobile: str, otp: str, country_code: str = "+91") -> Dict[str, Any]:
        auth_key = getattr(sys.modules[__name__], "MSG91_AUTH_KEY", "")
        sender_id = getattr(sys.modules[__name__], "MSG91_SENDER_ID", "")
        template_id = getattr(sys.modules[__name__], "MSG91_TEMPLATE_ID", "")

        if not (auth_key and template_id):
            return {
                "success": False,
                "provider": "msg91",
                "code": "MSG91_MISSING_CREDENTIALS",
                "delivery_id": None,
                "message": "Missing required MSG91 credentials in environment.",
            }

        url = "https://control.msg91.com/api/v5/otp"
        clean_mobile = to_mobile.replace("+", "").replace(" ", "").replace("-", "")
        if country_code and not clean_mobile.startswith(country_code.replace("+", "")):
            clean_mobile = f"{country_code.replace('+', '')}{clean_mobile}"

        logger.info("[SMS] Sending SMS OTP to %s via MSG91", mask_mobile_number(clean_mobile))
        headers = {
            "authkey": auth_key,
            "Content-Type": "application/json",
        }
        payload = {
            "template_id": template_id,
            "mobile": clean_mobile,
            "otp": otp,
        }
        if sender_id:
            payload["sender"] = sender_id

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    delivery_id = data.get("message", "msg91_ok")
                    logger.info("[SMS] MSG91 delivery SUCCESS")
                    return {
                        "success": True,
                        "provider": "msg91",
                        "delivery_id": delivery_id,
                        "message": "SMS verification code sent via MSG91.",
                    }
                else:
                    err_msg = resp.text[:200]
                    logger.error("[SMS] MSG91 rejected dispatch (HTTP %s): %s", resp.status_code, err_msg)
                    return {
                        "success": False,
                        "provider": "msg91",
                        "code": f"MSG91_{resp.status_code}",
                        "delivery_id": None,
                        "message": f"MSG91 API error (HTTP {resp.status_code})",
                    }
        except Exception as e:
            logger.error("[SMS] Network exception during MSG91 dispatch: %s", type(e).__name__)
            return {
                "success": False,
                "provider": "msg91",
                "code": "MSG91_NETWORK_ERROR",
                "delivery_id": None,
                "message": "Network error during MSG91 SMS dispatch.",
            }


class NullSMSProvider(BaseSMSProvider):
    """
    Null provider when SMS is unconfigured.
    NEVER fakes SMS delivery per Phase 6 requirements.
    """
    def send(self, to_mobile: str, otp: str, country_code: str = "+91") -> Dict[str, Any]:
        return {
            "success": False,
            "provider": "unconfigured",
            "code": "SMS_NOT_CONFIGURED",
            "delivery_id": None,
            "message": "Mobile verification is temporarily unavailable. Please try again later.",
        }


def get_sms_provider() -> str:
    """Determine the active SMS provider based on configuration."""
    provider_pref = getattr(sys.modules[__name__], "SMS_PROVIDER", "").strip().lower()
    sid = getattr(sys.modules[__name__], "TWILIO_ACCOUNT_SID", "")
    token = getattr(sys.modules[__name__], "TWILIO_AUTH_TOKEN", "")
    from_num = getattr(sys.modules[__name__], "TWILIO_FROM_NUMBER", "")
    msg91_key = getattr(sys.modules[__name__], "MSG91_AUTH_KEY", "")
    msg91_template = getattr(sys.modules[__name__], "MSG91_TEMPLATE_ID", "")

    if provider_pref == "twilio" and (sid and token and from_num):
        return "twilio"
    if provider_pref == "msg91" and (msg91_key and msg91_template):
        return "msg91"
    if sid and token and from_num:
        return "twilio"
    if msg91_key and msg91_template:
        return "msg91"
    return "unconfigured"


def get_sms_provider_instance() -> BaseSMSProvider:
    """Return an instantiated SMSProvider."""
    provider = get_sms_provider()
    if provider == "twilio":
        return TwilioSMSProvider()
    if provider == "msg91":
        return MSG91SMSProvider()
    return NullSMSProvider()


def get_sms_provider_status() -> Dict[str, Any]:
    """Return non-sensitive status information about SMS provider readiness."""
    provider = get_sms_provider()
    is_configured = provider in ("twilio", "msg91")
    sid = getattr(sys.modules[__name__], "TWILIO_ACCOUNT_SID", "")
    token = getattr(sys.modules[__name__], "TWILIO_AUTH_TOKEN", "")
    from_num = getattr(sys.modules[__name__], "TWILIO_FROM_NUMBER", "")
    msg91_key = getattr(sys.modules[__name__], "MSG91_AUTH_KEY", "")
    msg91_sender = getattr(sys.modules[__name__], "MSG91_SENDER_ID", "")
    msg91_template = getattr(sys.modules[__name__], "MSG91_TEMPLATE_ID", "")

    return {
        "provider": provider,
        "is_configured": is_configured,
        "ready": is_configured,
        "environment": getattr(sys.modules[__name__], "APP_ENV", "development"),
        "twilio_ready": bool(sid and token and from_num),
        "msg91_ready": bool(msg91_key and msg91_sender and msg91_template),
        "message": (
            f"SMS provider '{provider}' is active and ready."
            if is_configured
            else "Mobile verification is temporarily unavailable. Please try again later."
        ),
    }


def send_sms_otp(
    to_mobile: str,
    otp: str,
    country_code: str = "+91",
) -> Dict[str, Any]:
    """Primary SMS OTP entrypoint."""
    provider_inst = get_sms_provider_instance()
    return provider_inst.send(to_mobile, otp, country_code)
