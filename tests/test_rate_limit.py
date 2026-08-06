import asyncio

from app.bot.guards import rate_limit as rate_limit_module
from app.bot.guards.rate_limit import InMemoryRateLimiter
from app.database.base import Base as DatabaseBase
from app.database.base import Base as ModelsBase


class StubRedisCache:
    def __init__(self) -> None:
        self.calls: dict[str, int] = {}

    async def increment(
        self,
        key: str,
        *,
        window_seconds: int,
    ) -> int:
        self.calls[key] = self.calls.get(key, 0) + 1
        return self.calls[key]


class FailingRedisCache:
    async def increment(
        self,
        key: str,
        *,
        window_seconds: int,
    ) -> int:
        raise RuntimeError("redis unavailable")


def test_in_memory_rate_limiter_blocks_after_limit() -> None:
    limiter = InMemoryRateLimiter()

    assert limiter.is_allowed("user:1", limit=2, window_seconds=60)
    assert limiter.is_allowed("user:1", limit=2, window_seconds=60)
    assert not limiter.is_allowed("user:1", limit=2, window_seconds=60)


def test_in_memory_rate_limiter_is_scoped_per_key() -> None:
    limiter = InMemoryRateLimiter()

    assert limiter.is_allowed("user:1", limit=1, window_seconds=60)
    assert limiter.is_allowed("user:2", limit=1, window_seconds=60)
    assert not limiter.is_allowed("user:1", limit=1, window_seconds=60)


def test_database_base_is_unified() -> None:
    assert DatabaseBase is ModelsBase


def test_redis_rate_limiter_uses_redis_counter() -> None:
    rate_limit_module.configure_rate_limiter(StubRedisCache())

    allowed_first = asyncio.run(
        rate_limit_module.is_rate_limited_allowed(
            "key-1",
            limit=2,
            window_seconds=60,
        )
    )
    allowed_second = asyncio.run(
        rate_limit_module.is_rate_limited_allowed(
            "key-1",
            limit=2,
            window_seconds=60,
        )
    )
    blocked_third = asyncio.run(
        rate_limit_module.is_rate_limited_allowed(
            "key-1",
            limit=2,
            window_seconds=60,
        )
    )

    rate_limit_module.configure_rate_limiter(None)

    assert allowed_first is True
    assert allowed_second is True
    assert blocked_third is False


def test_redis_rate_limiter_falls_back_to_memory() -> None:
    rate_limit_module.configure_rate_limiter(FailingRedisCache())

    allowed_first = asyncio.run(
        rate_limit_module.is_rate_limited_allowed(
            "fallback-key",
            limit=1,
            window_seconds=60,
        )
    )
    blocked_second = asyncio.run(
        rate_limit_module.is_rate_limited_allowed(
            "fallback-key",
            limit=1,
            window_seconds=60,
        )
    )

    rate_limit_module.configure_rate_limiter(None)

    assert allowed_first is True
    assert blocked_second is False
