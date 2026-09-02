from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class MessengerPlatform(StrEnum):
    TELEGRAM_STANDARD = "telegram-standard"
    UNKNOWN = "unknown"


class MessengerFeature(StrEnum):
    INLINE_KEYBOARD = "inline_keyboard"
    CALLBACK_QUERY = "callback_query"
    PREMIUM = "premium"
    DONATE = "donate"
    STARS = "stars"
    GIFT = "gift"


@dataclass(frozen=True, slots=True)
class FeatureSupport:
    feature: MessengerFeature
    supported: bool
    platform: MessengerPlatform
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class CapabilityProfile:
    platform: MessengerPlatform
    feature_support: dict[MessengerFeature, bool]


@dataclass(frozen=True, slots=True)
class ProbeSpec:
    method: str
    http_method: str = "GET"
    payload: dict[str, Any] | None = None
    accepted_error_descriptions: tuple[str, ...] = ()
    accepted_status_codes: tuple[int, ...] = ()


class APIFeatureChecker:
    """
    Detects runtime bot capabilities by probing the configured Bot API.

    The probe checks whether specific Bot API routes exist and respond in a
    compatible way. Features are enabled only when the corresponding route is
    reachable and behaves as expected.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings: Settings = settings or get_settings()
        self._profile = CapabilityProfile(
            platform=MessengerPlatform.UNKNOWN,
            feature_support={feature: False for feature in MessengerFeature},
        )

    @property
    def platform(self) -> MessengerPlatform:
        return self._profile.platform

    async def detect(self) -> None:
        bot_api = (self._settings.BOT_API or "").rstrip("/")
        token = (self._settings.BOT_TOKEN or "").strip()

        if not bot_api or not token:
            logger.warning(
                "Skipping capability detection because BOT_API or BOT_TOKEN is empty."
            )
            return

        probe_map = {
            MessengerFeature.INLINE_KEYBOARD: ProbeSpec(method="getMe"),
            MessengerFeature.CALLBACK_QUERY: ProbeSpec(
                method="setMyCommands",
                http_method="POST",
                payload={"commands": []},
                accepted_error_descriptions=(
                    "bad request: commands are too much",
                    "bad request: can't parse botcommand",
                    "not implemented (coming soon...)",
                ),
                accepted_status_codes=(200, 400, 401, 403, 501),
            ),
            MessengerFeature.PREMIUM: ProbeSpec(method="getUserProfilePhotos"),
            MessengerFeature.DONATE: ProbeSpec(method="getMyCommands"),
            MessengerFeature.STARS: ProbeSpec(method="getStarTransactions"),
            MessengerFeature.GIFT: ProbeSpec(method="getAvailableGifts"),
        }

        feature_support: dict[MessengerFeature, bool] = {}

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=True,
        ) as client:
            for feature, spec in probe_map.items():
                supported = await self._probe_method(
                    client,
                    bot_api,
                    token,
                    spec,
                )
                feature_support[feature] = supported

        if feature_support.get(MessengerFeature.CALLBACK_QUERY):
            feature_support[MessengerFeature.INLINE_KEYBOARD] = True

        platform = (
            MessengerPlatform.TELEGRAM_STANDARD
            if any(feature_support.values())
            else MessengerPlatform.UNKNOWN
        )

        self._profile = CapabilityProfile(
            platform=platform,
            feature_support=feature_support,
        )

        logger.info(
            "Detected bot API capabilities: %s",
            {
                feature.value: supported
                for feature, supported in feature_support.items()
            },
        )

    async def _probe_method(
        self,
        client: httpx.AsyncClient,
        bot_api: str,
        token: str,
        spec: ProbeSpec,
    ) -> bool:
        url = f"{bot_api}/bot{token}/{spec.method}"

        try:
            if spec.http_method == "POST":
                response = await client.post(url, json=spec.payload)
            else:
                response = await client.get(url, params=spec.payload)
        except httpx.HTTPError as exc:
            # Mask token in logs by using a redacted URL
            redacted_url = f"{bot_api}/bot<REDACTED>/{spec.method}"
            logger.info("Capability probe failed for %s: %s", redacted_url, exc)
            return False

        try:
            payload = response.json()
        except ValueError:
            logger.info(
                "Capability probe for %s returned non-JSON response",
                spec.method,
            )
            return False

        if not isinstance(payload, dict):
            return False

        if payload.get("ok") is True:
            return True

        description = str(payload.get("description") or "").strip().lower()

        if response.status_code in spec.accepted_status_codes:
            return True

        if any(description == item for item in spec.accepted_error_descriptions):
            return True

        logger.info(
            "Capability probe for %s returned unsupported response: HTTP %s %s",
            spec.method,
            response.status_code,
            description or payload,
        )
        return False

    def supports(self, feature: MessengerFeature) -> bool:
        return self.describe(feature).supported

    def require(self, feature: MessengerFeature) -> None:
        support = self.describe(feature)

        if support.supported:
            return

        reason = support.reason or "unsupported feature"
        raise RuntimeError(
            f"Feature '{feature.value}' is not supported by '{support.platform.value}': {reason}"
        )

    def describe(self, feature: MessengerFeature) -> FeatureSupport:
        supported = self._profile.feature_support.get(feature, False)
        reason = None if supported else "feature probe failed or route is unavailable"

        return FeatureSupport(
            feature=feature,
            supported=supported,
            platform=self._profile.platform,
            reason=reason,
        )

    def log_if_unsupported(
        self,
        feature: MessengerFeature,
        *,
        context: str,
    ) -> bool:
        support = self.describe(feature)

        if support.supported:
            return True

        logger.warning(
            "Skipping unsupported feature '%s' for platform '%s' in %s: %s",
            feature.value,
            support.platform.value,
            context,
            support.reason or "unsupported",
        )
        return False
