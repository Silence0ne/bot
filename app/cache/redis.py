from __future__ import annotations

import logging

from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self):
        settings = get_settings()
        self.redis = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )

    async def increment(
        self,
        key: str,
        *,
        window_seconds: int,
    ) -> int:
        value = await self.redis.incr(key)
        if value == 1:
            await self.redis.expire(key, window_seconds)
        return int(value)

    async def connect(self):
        await self.redis.ping()
        logger.info("Redis connected.")

    async def close(self):
        await self.redis.aclose()
        logger.info("Redis disconnected.")
