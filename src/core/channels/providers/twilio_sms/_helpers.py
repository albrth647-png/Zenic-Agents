"""Helper methods extracted from twilio_sms."""

from __future__ import annotations

from ..._types import ChannelResponse, DeliveryStatus
from ..._formatter import format_sms_text

import logging
import time

logger = logging.getLogger(__name__)


def _dry_run_send(self, message: ChannelMessage) -> ChannelResponse:  # noqa: F821  # TODO: Phase3 - verify import
    """Log message without sending."""
    with self._lock:
        self._sent_count += 1

    text = format_sms_text(message)
    text_preview = text[:80]
    logger.info(
        "[SMS DRY-RUN] To: %s | Text: %s%s",
        message.recipient or "default",
        text_preview,
        "..." if len(text) > 80 else "",
    )

    return ChannelResponse(
        success=True,
        channel="sms",
        status=DeliveryStatus.DRY_RUN,
        metadata={"mode": "dry_run", "char_count": len(text)},
        timestamp=time.time(),
    )



