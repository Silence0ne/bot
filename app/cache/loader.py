from __future__ import annotations

import logging

import httpx

from app.api.provider import NatiqProvider
from app.cache.quran import QuranCache

logger = logging.getLogger(__name__)


class QuranCacheLoader:
    """
    Loads all Quran resources into memory.

    Startup order:

        1. Ayahs
        2. Takhtits
        3. Translations
        4. Surahs

    After this finishes, every lookup performed by the provider
    is O(1) through the cache lookup tables.
    """

    def __init__(
        self,
        provider: NatiqProvider,
        cache: QuranCache,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self.loading = False

    async def load(self) -> bool:
        logger.info("Loading Quran cache...")
        self.loading = True

        try:
            await self._load_ayahs()
            await self._load_takhtits()
            await self._load_translations()
            await self._load_surahs()
        except (httpx.HTTPError, RuntimeError) as exc:
            logger.exception("Quran cache loading failed: %s", exc)
            self.loading = False
            return False

        logger.info("Quran cache loaded successfully.")
        self.loading = False
        return True

    async def _load_ayahs(self) -> None:
        ayahs = await self._provider.list_ayahs()
        self._cache.set_ayahs(ayahs)

        if len(ayahs) != 6236:
            logger.warning("Unexpected ayah count: %s", len(ayahs))

    async def _load_takhtits(self) -> None:
        takhtits = await self._provider.list_takhtits()
        self._cache.set_takhtits(takhtits)

        if len(takhtits) != len(self._cache.ayahs):
            logger.warning(
                "Takhtit count (%s) does not match ayah count (%s).",
                len(takhtits),
                len(self._cache.ayahs),
            )

    async def _load_translations(self) -> None:
        translations = await self._provider.list_translations()
        self._cache.set_translations(translations)

        if not translations:
            logger.warning("No translations were loaded.")

    async def _load_surahs(self) -> None:
        surahs = await self._provider.list_surahs()
        self._cache.set_surahs(surahs)

        if len(surahs) != 114:
            logger.warning("Unexpected surah count: %s", len(surahs))
