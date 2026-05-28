"""twilio_sms — Transport mixin (API calls, webhook, dry run)."""

from __future__ import annotations

import asyncio
import base64
import json
import time
import urllib
import urllib.parse
import urllib.request

from ._types import _HTTP_TIMEOUT, _MAX_RETRIES, _RETRY_BASE_DELAY, _validate_url


class TwilioSMSTransportMixin:
    """Transport methods for TwilioSMSChannelProvider."""

    # ── Internal: API ───────────────────────────────────────────

    async def _post_api(self, payload: dict[str, str]) -> ChannelResponse:  # noqa: F821
        """POST to Twilio Messages API (form-encoded)."""
        url = _validate_url(f"{self._api_base}/Accounts/{self._account_sid}/Messages.json")

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                if _HAS_AIOHTTP and self._session:  # noqa: F821
                    return await self._post_api_aiohttp(url, payload)
                elif _HAS_URLLIB:  # noqa: F821
                    return await self._post_api_urllib(url, payload)
                else:
                    return ChannelResponse(  # noqa: F821  # TODO: add import
                        success=False,
                        channel="sms",
                        status=DeliveryStatus.FAILED,  # noqa: F821
                        error="No HTTP library available",
                        timestamp=time.time(),
                    )
            except Exception as e:
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                else:
                    return ChannelResponse(  # noqa: F821  # TODO: add import
                        success=False,
                        channel="sms",
                        status=DeliveryStatus.FAILED,  # noqa: F821
                        error=f"HTTP error after {_MAX_RETRIES} attempts: {e}",
                        timestamp=time.time(),
                    )

        return ChannelResponse(  # noqa: F821  # TODO: add import
            success=False,
            channel="sms",
            status=DeliveryStatus.FAILED,  # noqa: F821
            error="Unexpected retry loop exit",
            timestamp=time.time(),
        )

    async def _post_api_aiohttp(
        self,
        url: str,
        payload: dict[str, str],
    ) -> ChannelResponse:  # noqa: F821  # TODO: add import
        """Send via aiohttp (form-encoded)."""
        assert self._session is not None

        async with self._session.post(url, data=payload) as resp:
            body = await resp.json()

            if resp.status in (201, 200):
                msg_sid = body.get("sid", "")
                return ChannelResponse(  # noqa: F821  # TODO: add import
                    success=True,
                    channel="sms",
                    message_id=msg_sid,
                    status=DeliveryStatus.SENT,  # noqa: F821
                    metadata={"twilio_sid": msg_sid, "status": body.get("status", "")},
                    timestamp=time.time(),
                )
            elif resp.status == 429:
                return ChannelResponse(  # noqa: F821  # TODO: add import
                    success=False,
                    channel="sms",
                    status=DeliveryStatus.RATE_LIMITED,  # noqa: F821
                    error=f"Rate limited: {body}",
                    timestamp=time.time(),
                )
            else:
                error_msg = body.get("message", str(body)[:200])
                return ChannelResponse(  # noqa: F821  # TODO: add import
                    success=False,
                    channel="sms",
                    status=DeliveryStatus.FAILED,  # noqa: F821
                    error=f"Twilio API error ({resp.status}): {error_msg}",
                    timestamp=time.time(),
                )

    async def _post_api_urllib(
        self,
        url: str,
        payload: dict[str, str],
    ) -> ChannelResponse:  # noqa: F821  # TODO: add import
        """Send via urllib (sync, wrapped in asyncio.to_thread)."""

        def _sync_post() -> ChannelResponse:  # noqa: F821  # TODO: add import
            credentials = base64.b64encode(f"{self._account_sid}:{self._auth_token}".encode()).decode("utf-8")

            encoded = urllib.parse.urlencode(payload).encode("utf-8")
            req = urllib.request.Request(  # noqa: S310
                url,
                data=encoded,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:  # noqa: S310
                    body = json.loads(resp.read().decode("utf-8"))
                    msg_sid = body.get("sid", "")
                    return ChannelResponse(  # noqa: F821  # TODO: add import
                        success=True,
                        channel="sms",
                        message_id=msg_sid,
                        status=DeliveryStatus.SENT,  # noqa: F821
                        metadata={"twilio_sid": msg_sid},
                        timestamp=time.time(),
                    )
            except urllib.error.HTTPError as e:
                body = e.read().decode()[:300]
                if e.code == 429:
                    return ChannelResponse(  # noqa: F821  # TODO: add import
                        success=False,
                        channel="sms",
                        status=DeliveryStatus.RATE_LIMITED,  # noqa: F821
                        error="Rate limited",
                        timestamp=time.time(),
                    )
                return ChannelResponse(  # noqa: F821  # TODO: add import
                    success=False,
                    channel="sms",
                    status=DeliveryStatus.FAILED,  # noqa: F821
                    error=f"HTTP {e.code}: {body}",
                    timestamp=time.time(),
                )
            except Exception as e:
                return ChannelResponse(  # noqa: F821  # TODO: add import
                    success=False,
                    channel="sms",
                    status=DeliveryStatus.FAILED,  # noqa: F821
                    error=f"urllib error: {e}",
                    timestamp=time.time(),
                )

        return await asyncio.to_thread(_sync_post)
