from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass
from functools import wraps
from inspect import isawaitable
from typing import Protocol

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from app.core.config import get_settings
from app.i18n import detect_language, get_message


class SupportsRateLimitIncrement(Protocol):
    async def increment(
        self,
        key: str,
        *,
        window_seconds: int,
    ) -> int: ...


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int
    message: str | None = None


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}

    def is_allowed(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
    ) -> bool:
        now = time.monotonic()
        window_start = now - window_seconds
        hits = self._hits.setdefault(key, deque())

        while hits and hits[0] <= window_start:
            _ = hits.popleft()

        if len(hits) >= limit:
            return False

        hits.append(now)
        return True


class RedisRateLimiter:
    def __init__(self, redis_cache: SupportsRateLimitIncrement) -> None:
        self._redis_cache: SupportsRateLimitIncrement = redis_cache

    async def is_allowed(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
    ) -> bool:
        current = await self._redis_cache.increment(
            key,
            window_seconds=window_seconds,
        )
        return current <= limit


_memory_rate_limiter = InMemoryRateLimiter()
_redis_rate_limiter: RedisRateLimiter | None = None


def configure_rate_limiter(
    redis_cache: SupportsRateLimitIncrement | None,
) -> None:
    global _redis_rate_limiter

    if redis_cache is None:
        _redis_rate_limiter = None
        return

    _redis_rate_limiter = RedisRateLimiter(redis_cache)


def _resolve_actor_key(update: Update) -> str | None:
    chat = update.effective_chat

    if chat and chat.id is not None:
        return f"chat:{chat.id}"

    return None


async def _reply_rate_limited(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message: str,
) -> None:
    settings = get_settings()
    message_with_username = f"{message}\n\n📱 {settings.BOT_USERNAME}"

    if update.callback_query is not None:
        try:
            await update.callback_query.answer(
                message_with_username,
                show_alert=False,
            )
        except BadRequest:
            # Query already answered or expired; fall back to editing the message.
            try:
                await update.callback_query.edit_message_text(message_with_username)
            except BadRequest:
                pass
        return

    if update.message is not None:
        await update.message.reply_text(message_with_username)
        return

    if update.effective_chat is not None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message_with_username,
        )


async def is_rate_limited_allowed(
    key: str,
    *,
    limit: int,
    window_seconds: int,
) -> bool:
    if _redis_rate_limiter is not None:
        try:
            return await _redis_rate_limiter.is_allowed(
                key,
                limit=limit,
                window_seconds=window_seconds,
            )
        except Exception as exc:
            logger.warning(
                "Redis rate limiter failed, falling back to memory: %s",
                exc,
            )

    return _memory_rate_limiter.is_allowed(
        key,
        limit=limit,
        window_seconds=window_seconds,
    )


def rate_limit(rule: RateLimitRule):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> object | None:
            update = kwargs.get("update")
            context = kwargs.get("context")

            if update is None and args:
                candidate_update = args[0]
                if isinstance(candidate_update, Update):
                    update = candidate_update

            if context is None and len(args) > 1:
                candidate_context = args[1]
                if hasattr(candidate_context, "bot"):
                    context = candidate_context

            if not isinstance(update, Update) or context is None:
                result = func(*args, **kwargs)
                if isawaitable(result):
                    return await result
                return result

            typed_update: Update = update
            typed_context = context

            actor_key = _resolve_actor_key(typed_update)

            if actor_key is None:
                result = func(*args, **kwargs)
                if isawaitable(result):
                    return await result
                return result

            allowed = await is_rate_limited_allowed(
                f"rate_limit:{func.__module__}.{func.__name__}:{actor_key}",
                limit=rule.limit,
                window_seconds=rule.window_seconds,
            )

            if not allowed:
                language = detect_language(
                    typed_update.effective_user.language_code
                    if typed_update.effective_user
                    else None
                )

                message = rule.message or get_message(
                    "rate_limited",
                    language,
                )

                await _reply_rate_limited(
                    typed_update,
                    typed_context,
                    message,
                )
                return None

            result = func(*args, **kwargs)
            if isawaitable(result):
                return await result
            return result

        return wrapper

    return decorator
