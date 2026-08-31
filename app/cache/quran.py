from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class QuranCache:
    """
    In-memory Quran cache.

    Stores raw API data and optimized lookup maps.

    Relationships:

    Ayah UUID
        ↓
    Takhtit metadata
        ↓
    Surah number / UUID
        ↓
    Surah information
    """

    def __init__(self) -> None:
        self.ayahs: list[dict[str, Any]] = []
        self.takhtits: list[dict[str, Any]] = []
        self.translations: list[dict[str, Any]] = []
        self.surahs: list[dict[str, Any]] = []

        self.ayah_map: dict[str, dict[str, Any]] = {}
        self.takhtit_map: dict[str, dict[str, Any]] = {}
        self.translation_map: dict[str, dict[str, Any]] = {}

        self.surah_map: dict[int, dict[str, Any]] = {}
        self.surah_uuid_map: dict[str, dict[str, Any]] = {}

        # Page indexes (built once ayahs + takhtits are available).
        # page_ayahs maps a page number to the ordered list of ayah UUIDs on it.
        self.page_ayahs: dict[int, list[str]] = {}
        # uuid_page maps an ayah UUID to its page number (when known).
        self.uuid_page: dict[str, int] = {}

    def set_ayahs(self, items: list[dict[str, Any]]) -> None:
        self.ayahs = items
        self.ayah_map = {item["uuid"]: item for item in items if item.get("uuid")}

        # Page indexes can only be built once takhtit metadata is present.
        self._clear_page_indexes()

        logger.info("Cached %s ayahs", len(self.ayahs))

    def set_takhtits(self, items: list[dict[str, Any]]) -> None:
        self.takhtits = items
        self.takhtit_map = {item["uuid"]: item for item in items if item.get("uuid")}

        self._build_page_indexes()

        logger.info("Cached %s takhtits", len(self.takhtits))

    @staticmethod
    def _extract_page(
        ayah: dict[str, Any], takhtit_map: dict[str, dict[str, Any]]
    ) -> int | None:
        """Resolve the page number for an ayah, replicating provider fallback."""
        metadata = takhtit_map.get(ayah.get("uuid", ""))
        if metadata and metadata.get("page") is not None:
            return int(metadata["page"])

        for breaker in ayah.get("breakers") or []:
            if not isinstance(breaker, dict):
                continue
            if breaker.get("name") == "page" and breaker.get("number") is not None:
                return int(breaker["number"])

        return None

    def _clear_page_indexes(self) -> None:
        self.page_ayahs = {}
        self.uuid_page = {}

    def _build_page_indexes(self) -> None:
        self._clear_page_indexes()

        for ayah in self.ayahs:
            ayah_uuid = ayah.get("uuid")
            if not ayah_uuid:
                continue

            page = self._extract_page(ayah, self.takhtit_map)
            if page is None:
                continue

            self.uuid_page[ayah_uuid] = page
            self.page_ayahs.setdefault(page, []).append(ayah_uuid)

        logger.info(
            "Indexed %s pages for %s ayahs",
            len(self.page_ayahs),
            len(self.uuid_page),
        )

    def set_translations(self, items: list[dict[str, Any]]) -> None:
        self.translations = items
        self.translation_map = {
            item["ayah_uuid"]: item for item in items if item.get("ayah_uuid")
        }

        logger.info("Cached %s translations", len(self.translations))

    def set_surahs(self, items: list[dict[str, Any]]) -> None:
        self.surahs = items
        self.surah_map = {}
        self.surah_uuid_map = {}

        for surah in items:
            number = surah.get("number")
            uuid = surah.get("uuid")

            if number is not None:
                self.surah_map[int(number)] = surah

            if uuid:
                self.surah_uuid_map[str(uuid)] = surah

        logger.info("Cached %s surahs", len(self.surahs))
        logger.info("Surah number map: %s", len(self.surah_map))
        logger.info("Surah UUID map: %s", len(self.surah_uuid_map))
