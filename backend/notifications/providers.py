"""Provider abstraction for external notification delivery channels (SMS via Twilio)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ml.common.logging_config import get_logger

logger = get_logger("backend.notifications.providers")


class NotificationProviderError(Exception):
    """Base exception for notification provider delivery failures."""

    pass


class SMSProvider(ABC):
    """Abstract interface for SMS notification providers."""

    @abstractmethod
    def send_sms(self, recipient_phone: str, message: str) -> bool:
        """Send SMS message to target phone number. Return True on success."""
        pass


class TwilioSMSProvider(SMSProvider):
    """Twilio SMS provider implementation."""

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_phone: Optional[str] = None,
        enabled: bool = True,
    ) -> None:
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_phone = from_phone
        self.enabled = enabled

    def is_configured(self) -> bool:
        """Check if Twilio credentials and sender number are fully configured."""
        return bool(self.enabled and self.account_sid and self.auth_token and self.from_phone)

    def send_sms(self, recipient_phone: str, message: str) -> bool:
        """Deliver SMS message via Twilio API client."""
        if not self.enabled:
            logger.info("SMS delivery skipped: Twilio SMS is disabled in settings.")
            return False

        if not self.is_configured():
            logger.info("SMS delivery skipped: Twilio credentials/phone number unconfigured.")
            return False

        if not recipient_phone or not recipient_phone.strip():
            logger.warning("SMS delivery skipped: Recipient phone number is empty.")
            return False

        try:
            from twilio.rest import Client

            client = Client(self.account_sid, self.auth_token)
            msg = client.messages.create(
                body=message,
                from_=self.from_phone,
                to=recipient_phone.strip(),
            )
            logger.info(f"Twilio SMS dispatched successfully. SID: {getattr(msg, 'sid', 'mock_sid')}")
            return True
        except ImportError:
            logger.warning("twilio package not installed. Skipping Twilio dispatch.")
            return False
        except Exception as exc:
            logger.error(f"Twilio SMS delivery failed for phone '{recipient_phone}': {exc}")
            raise NotificationProviderError(f"Twilio SMS failure: {str(exc)}") from exc
