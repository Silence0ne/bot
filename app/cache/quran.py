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
        # surah_ayahs maps a surah number to {ayah_number: ayah_uuid} for
        # O(1) next/prev ayah navigation within a surah.
        self.surah_ayahs: dict[int, dict[int, str]] = {}
        # uuid_surah_ayah maps an ayah UUID -> (surah_number, ayah_number).
        self.uuid_surah_ayah: dict[str, tuple[int, int]] = {}

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
    def _extract_metadata(
        ayah: dict[str, Any], takhtit_map: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """Resolve surah/ayah/page metadata for an ayah, replicating provider fallback."""
        uuid = ayah.get("uuid", "")
        metadata = takhtit_map.get(uuid)
        if not metadata:
            metadata = {}

        result: dict[str, Any] = {}

        if metadata.get("surah") is not None:
            result["surah"] = int(metadata["surah"])

        if metadata.get("ayah") is not None:
            result["ayah"] = int(metadata["ayah"])

        if metadata.get("page") is not None:
            result["page"] = int(metadata["page"])

        # Fall back to the position fields embedded in the ayah itself.
        surah_obj = ayah.get("surah")
        if isinstance(surah_obj, dict) and surah_obj.get("number") is not None:
            result.setdefault("surah", int(surah_obj["number"]))

        if ayah.get("number") is not None:
            result.setdefault("ayah", int(ayah["number"]))

        for breaker in ayah.get("breakers") or []:
            if not isinstance(breaker, dict):
                continue
            name = breaker.get("name")
            value = breaker.get("number")
            if value is None or not isinstance(name, str):
                continue
            if name == "page":
                result.setdefault("page", int(value))
            elif name == "surah":
                result.setdefault("surah", int(value))

        return result

    def _clear_page_indexes(self) -> None:
        self.page_ayahs = {}
        self.uuid_page = {}
        self.surah_ayahs = {}
        self.uuid_surah_ayah = {}

    def _build_page_indexes(self) -> None:
        self._clear_page_indexes()

        for ayah in self.ayahs:
            ayah_uuid = ayah.get("uuid")
            if not ayah_uuid:
                continue

            metadata = self._extract_metadata(ayah, self.takhtit_map)

            page = metadata.get("page")
            if page is not None:
                self.uuid_page[ayah_uuid] = page
                self.page_ayahs.setdefault(page, []).append(ayah_uuid)

            surah = metadata.get("surah")
            ayah_number = metadata.get("ayah")
            if surah is not None and ayah_number is not None:
                self.surah_ayahs.setdefault(surah, {})[ayah_number] = ayah_uuid
                self.uuid_surah_ayah[ayah_uuid] = (surah, ayah_number)

        logger.info(
            "Indexed %s pages (%s ayahs) and %s surahs for next/prev navigation",
            len(self.page_ayahs),
            len(self.uuid_page),
            len(self.surah_ayahs),
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
