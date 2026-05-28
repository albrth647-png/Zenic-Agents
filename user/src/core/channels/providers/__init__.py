"""
ZENIC-AGENTS — Channel Providers

Phase 1 implementations:
  - TeamsChannelProvider    — Microsoft Teams (Incoming Webhooks + Adaptive Cards)
  - SlackChannelProvider    — Slack (Block Kit + Events API / Socket Mode)
  - WhatsAppChannelProvider — WhatsApp Business Cloud API
  - TwilioSMSChannelProvider — SMS/MMS via Twilio

Phase 2 implementations:
  - PushChannelProvider     — Push Notifications (Web Push VAPID + FCM HTTP v1)
  - EmailChannelProvider    — Email (SMTP + Microsoft Graph API)
"""

from .email import EmailChannelProvider
from .push import PushChannelProvider
from .slack import SlackChannelProvider
from .teams import TeamsChannelProvider
from .twilio_sms import TwilioSMSChannelProvider
from .whatsapp import WhatsAppChannelProvider

__all__ = [
    "EmailChannelProvider",
    "PushChannelProvider",
    "SlackChannelProvider",
    "TeamsChannelProvider",
    "TwilioSMSChannelProvider",
    "WhatsAppChannelProvider",
]
