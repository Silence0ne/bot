from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import httpx

from app.api.client import APIClient
from app.cache.quran import QuranCache
from app.core.config import get_settings
from app.schemas.ayah import Ayah

logger = logging.getLogger(__name__)


class NatiqProvider:
    def __init__(
        self,
        client: APIClient,
        cache: QuranCache,
    ) -> None:
        self._client = client
        self._cache = cache
        self._settings = get_settings()
        self._takhtit_uuids: list[str] | None = None

    async def _get_with_retry(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        retries: int = 3,
    ) -> Any:
        last_error: Exception | None = None

        for attempt in range(retries):
            try:
                return await self._client.get(
                    endpoint,
                    params=params,
                )
            except httpx.HTTPError as exc:
                last_error = exc

                logger.warning(
                    "Request failed %s attempt %s/%s: %s",
                    endpoint,
                    attempt + 1,
                    retries,
                    exc,
                )

                await asyncio.sleep(2**attempt)

        raise RuntimeError(f"Request failed: {endpoint}") from last_error

    @staticmethod
    def _extract_list(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload

        if isinstance(payload, dict):
            return payload.get("results") or payload.get("data") or []

        return []

    async def _list_takhtit_uuids(self) -> list[str]:
        if self._takhtit_uuids is not None:
            return self._takhtit_uuids

        response = await self._get_with_retry("/takhtits/")
        data = response.json()

        uuids: list[str] = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    u = item.get("uuid")
                    if isinstance(u, str) and u:
                        uuids.append(u)

        if not uuids:
            logger.warning("No takhtits found from /takhtits/")
        else:
            logger.info("Found %s takhtit uuids", len(uuids))

        self._takhtit_uuids = uuids
        return uuids

    async def list_ayahs(self) -> list[dict[str, Any]]:
        logger.info("Loading ayahs...")

        results: list[dict[str, Any]] = []
        offset = 0
        limit = 200

        while True:
            response = await self._get_with_retry(
                "/ayahs/",
                params={
                    "mushaf": self._settings.QURAN_MUSHAF,
                    "offset": offset,
                    "limit": limit,
                },
            )

            items = self._extract_list(response.json())

            if not items:
                break

            results.extend(items)
            logger.info("Loaded %s ayahs", len(results))

            if len(items) < limit:
                break

            offset += len(items)

        logger.info("Finished loading %s ayahs", len(results))
        return results

    async def list_takhtits(self) -> list[dict[str, Any]]:
        logger.info("Loading takhtits...")

        uuids = await self._list_takhtit_uuids()
        if not uuids:
            return []

        # Choose strategy: use first UUID only (matches your earlier behavior).
        # If you want to load all UUIDs, tell me and I'll adjust.
        takhtit_uuid = uuids[0]
        logger.info("Using takhtit_uuid=%s", takhtit_uuid)

        results: list[dict[str, Any]] = []
        seen: set[str] = set()

        offset = 0
        limit = 200

        while True:
            response = await self._get_with_retry(
                f"/takhtits/{takhtit_uuid}/ayahs_breakers/",
                params={"offset": offset, "limit": limit},
            )

            items = self._extract_list(response.json())
            if not items:
                break

            added = 0
            for item in items:
                item_uuid = item.get("uuid")
                if isinstance(item_uuid, str) and item_uuid:
                    if item_uuid in seen:
                        continue
                    seen.add(item_uuid)

                results.append(item)
                added += 1

            logger.info("Loaded %s takhtits", len(results))

            if added == 0:
                logger.warning("Repeated takhtit page detected")
                break

            if len(items) < limit:
                break

            offset += len(items)

        logger.info("Finished loading %s takhtits", len(results))
        return results

    async def list_surahs(self) -> list[dict[str, Any]]:
        logger.info("Loading surahs...")

        response = await self._get_with_retry(
            "/surahs/",
            params={
                "mushaf": self._settings.QURAN_MUSHAF,
            },
        )

        surahs = self._extract_list(response.json())

        logger.info("Loaded %s surahs", len(surahs))
        return surahs

    async def list_translations(self) -> list[dict[str, Any]]:
        try:
            response = await self._get_with_retry(
                "/translations/",
                params={
                    "language": self._settings.QURAN_TRANSLATION_LANGUAGE,
                    "mushaf": self._settings.QURAN_MUSHAF,
                },
            )

            translations = self._extract_list(response.json())

            if not translations:
                logger.warning("No translations found")
                return []

            selected = None
            wanted = self._settings.QURAN_TRANSLATOR

            if wanted:
                for item in translations:
                    translator = item.get("translator", {})

                    if (
                        isinstance(translator, dict)
                        and translator.get("name") == wanted
                    ):
                        selected = item
                        break

            if selected is None:
                selected = translations[0]

            translation_uuid = selected.get("uuid")

            if not translation_uuid:
                return []

            results: list[dict[str, Any]] = []
            offset = 0
            limit = 200

            while True:
                response = await self._get_with_retry(
                    f"/translations/{translation_uuid}/ayahs/",
                    params={
                        "offset": offset,
                        "limit": limit,
                    },
                )

                items = self._extract_list(response.json())

                if not items:
                    break

                results.extend(items)

                if len(items) < limit:
                    break

                offset += len(items)

            logger.info("Finished loading %s translations", len(results))
            return results

        except httpx.HTTPError as exc:
            logger.warning("Translation loading failed: %s", exc)
            return []

    def _get_ayah_metadata(self, ayah: dict[str, Any]) -> dict[str, Any]:
        ayah_uuid = ayah.get("uuid")

        if not ayah_uuid:
            return {}

        return self._cache.takhtit_map.get(ayah_uuid, {})

    def _resolve_surah(self, metadata: dict[str, Any]) -> dict[str, Any]:
        surah_uuid = metadata.get("surah_uuid")

        if surah_uuid:
            surah = self._cache.surah_uuid_map.get(surah_uuid)
            if surah:
                return surah

        surah_number = metadata.get("surah")

        if surah_number is None:
            return {}

        return self._cache.surah_map.get(surah_number, {})

    @staticmethod
    def _get_surah_name(surah: dict[str, Any]) -> str:
        names = surah.get("names")

        if isinstance(names, list):
            for item in names:
                if not isinstance(item, dict):
                    continue

                name = item.get("name")
                if name:
                    return str(name)

        return str(
            surah.get("name")
            or surah.get("title")
            or surah.get("arabic_name")
            or surah.get("name_ar")
            or ""
        )

    @staticmethod
    def _get_surah_period(surah: dict[str, Any]) -> str:
        location = (
            str(
                surah.get("location")
                or surah.get("period")
                or surah.get("revelation_place")
                or ""
            )
            .strip()
            .lower()
        )

        if location in {"makki", "meccan", "makkah", "macca"}:
            return "makki"

        if location in {"madani", "medinan", "madinah", "medina"}:
            return "madani"

        return "unknown"

    def _get_surah_icon(self, surah: dict[str, Any]) -> str:
        period = self._get_surah_period(surah)

        if period == "makki":
            return "🕋"

        if period == "madani":
            return "🕌"

        return ""

    @staticmethod
    def _get_surah_bismillah(surah: dict[str, Any]) -> dict[str, Any]:
        bismillah = surah.get("bismillah")

        if isinstance(bismillah, dict):
            return bismillah

        return {}

    @classmethod
    def _get_surah_bismillah_text(cls, surah: dict[str, Any]) -> str | None:
        text = str(cls._get_surah_bismillah(surah).get("text") or "").strip()
        return text or None

    @classmethod
    def _is_surah_bismillah_ayah(cls, surah: dict[str, Any]) -> bool:
        return bool(cls._get_surah_bismillah(surah).get("is_ayah", False))

    @classmethod
    def _should_show_bismillah_line(
        cls,
        surah: dict[str, Any],
        ayah_number: int,
    ) -> bool:
        if ayah_number != 1:
            return False

        bismillah_text = cls._get_surah_bismillah_text(surah)

        if not bismillah_text:
            return False

        return not cls._is_surah_bismillah_ayah(surah)

    @classmethod
    def _normalize_ayah_text(
        cls,
        surah: dict[str, Any],
        ayah_number: int,
        text: str,
    ) -> str:
        normalized_text = text.strip()

        if ayah_number != 1:
            return normalized_text

        if not cls._is_surah_bismillah_ayah(surah):
            return normalized_text

        bismillah_text = cls._get_surah_bismillah_text(surah)

        if not bismillah_text:
            return normalized_text

        if normalized_text == bismillah_text:
            return normalized_text

        if normalized_text.startswith(f"{bismillah_text} "):
            return normalized_text[len(bismillah_text) :].strip()

        return normalized_text

    def _build_ayah_from_item(self, ayah: dict[str, Any]) -> Ayah:
        metadata = self._get_ayah_metadata(ayah)
        surah_number = metadata.get("surah", 0)
        ayah_number = metadata.get("ayah", ayah.get("number", 0))
        ayah_uuid = ayah.get("uuid", "")

        translation_item = self._cache.translation_map.get(ayah_uuid, {})
        translation = translation_item.get("text")
        surah = self._resolve_surah(metadata)
        bismillah_text = self._get_surah_bismillah_text(surah)
        show_bismillah_line = self._should_show_bismillah_line(
            surah,
            ayah_number,
        )

        return Ayah(
            text=self._normalize_ayah_text(
                surah,
                ayah_number,
                ayah.get("text", ""),
            ),
            uuid=ayah_uuid,
            translation=translation,
            surah_uuid=surah.get("uuid", ""),
            surah_name=self._get_surah_name(surah),
            surah_number=surah_number,
            surah_period=self._get_surah_period(surah),
            surah_icon=self._get_surah_icon(surah),
            bismillah_text=bismillah_text,
            bismillah_is_ayah=self._is_surah_bismillah_ayah(surah),
            show_bismillah_line=show_bismillah_line,
            ayah_number=ayah_number,
            page=metadata.get("page"),
            juz=metadata.get("juz"),
        )

    async def random_ayah(self) -> Ayah:
        if not self._cache.ayahs:
            raise RuntimeError("Quran cache empty")

        ayah = random.choice(self._cache.ayahs)
        return self._build_ayah_from_item(ayah)

    async def next_ayah(self, current_uuid: str | None = None) -> Ayah:
        return await self._navigate_ayah(
            current_uuid=current_uuid,
            direction="next",
        )

    async def _navigate_ayah(
        self,
        current_uuid: str | None = None,
        *,
        direction: str,
    ) -> Ayah:
        if not self._cache.ayahs:
            raise RuntimeError("Quran cache empty")

        if current_uuid is None:
            return await self.random_ayah()

        current_ayah = next(
            (ayah for ayah in self._cache.ayahs if ayah.get("uuid") == current_uuid),
            None,
        )

        if current_ayah is None:
            return await self.random_ayah()

        metadata = self._get_ayah_metadata(current_ayah)
        current_surah = metadata.get("surah", 0)
        current_number = metadata.get("ayah", current_ayah.get("number", 0))

        for ayah in self._cache.ayahs:
            if ayah.get("uuid") == current_uuid:
                continue

            candidate_metadata = self._get_ayah_metadata(ayah)
            candidate_surah = candidate_metadata.get("surah", 0)
            candidate_number = candidate_metadata.get("ayah", ayah.get("number", 0))

            if candidate_surah != current_surah:
                continue

            if direction == "next":
                if candidate_number == current_number + 1:
                    return self._build_ayah_from_item(ayah)
            else:
                if candidate_number == current_number - 1:
                    return self._build_ayah_from_item(ayah)

        current_index = next(
            index
            for index, ayah in enumerate(self._cache.ayahs)
            if ayah.get("uuid") == current_uuid
        )

        delta = 1 if direction == "next" else -1
        next_index = (current_index + delta) % len(self._cache.ayahs)
        ayah = self._cache.ayahs[next_index]

        return self._build_ayah_from_item(ayah)
