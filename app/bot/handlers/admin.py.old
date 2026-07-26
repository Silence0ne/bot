from __future__ import annotations

from typing import Protocol

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from app.api.checker import MessengerFeature
from app.bot.guards.rate_limit import RateLimitRule, rate_limit
from app.core.config import get_settings
from app.core.container import Container
from app.i18n import detect_language, get_message
from app.ui.keyboards import main_menu_keyboard


class SupportsAdminLookup(Protocol):
    async def is_admin(self, telegram_id: int) -> bool: ...


async def _resolve_is_admin(
    telegram_id: int,
    *,
    configured_admin_ids: set[int],
    user_repository: SupportsAdminLookup,
) -> bool:
    """
    A user is an admin if either is true:

    - their numeric ID is listed in the `ADMIN_USER_IDS` setting, or
    - their `users.is_admin` database column is set to true.

    The env-based check is tried first since it never requires a
    database round-trip.
    """
    if telegram_id in configured_admin_ids:
        return True

    return await user_repository.is_admin(telegram_id)


async def _is_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    user = update.effective_user

    if user is None or user.id is None:
        return False

    settings = get_settings()
    container: Container = context.application.bot_data["container"]

    return await _resolve_is_admin(
        user.id,
        configured_admin_ids=settings.admin_user_ids,
        user_repository=container.user_repository,
    )


def _build_admin_dashboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    language: str,
) -> str:
    settings = get_settings()
    container: Container = context.application.bot_data["container"]
    feature_checker = context.application.bot_data["feature_checker"]
    user_id = update.effective_user.id if update.effective_user else None

    callback_query_supported = feature_checker.supports(MessengerFeature.CALLBACK_QUERY)
    inline_keyboard_supported = feature_checker.supports(
        MessengerFeature.INLINE_KEYBOARD
    )

    return get_message("admin_dashboard", language).format(
        user_id=user_id or "-",
        platform=settings.PLATFORM,
        bot_language=settings.BOT_LANGUAGE,
        quran_cache_ready="yes" if container.quran_cache_ready else "no",
        inline_keyboard_supported="yes" if inline_keyboard_supported else "no",
        callback_query_supported="yes" if callback_query_supported else "no",
        configured_admin_count=len(settings.admin_user_ids),
    )


async def _reply_admin_denied(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.message:
        return

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    await update.message.reply_text(
        get_message("admin_access_denied", language),
        reply_markup=main_menu_keyboard(language),
    )


@rate_limit(
    RateLimitRule(
        limit=1,
        window_seconds=60,
    )
)
async def reload_quran_cache(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Admin-only command to reload the in-memory Quran cache without
    restarting the bot process.

    Rate-limited more strictly than other admin actions because it
    triggers a full re-fetch of the Quran dataset from the Natiq API.
    """
    if not update.message:
        return

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    if not await _is_admin(update, context):
        await _reply_admin_denied(update, context)
        return

    container: Container = context.application.bot_data["container"]

    await update.message.reply_text(get_message("admin_cache_reloading", language))

    reloaded = await container.reload_quran_cache()

    result_key = (
        "admin_cache_reload_success" if reloaded else "admin_cache_reload_failed"
    )

    await update.message.reply_text(
        get_message(result_key, language),
        reply_markup=main_menu_keyboard(language),
    )


@rate_limit(
    RateLimitRule(
        limit=5,
        window_seconds=15,
    )
)
async def admin_settings_entry(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.message:
        return

    if not await _is_admin(update, context):
        await _reply_admin_denied(update, context)
        return

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    await update.message.reply_text(
        _build_admin_dashboard(update, context, language),
        reply_markup=main_menu_keyboard(language),
    )


def get_command_handler() -> CommandHandler:
    return CommandHandler("admin", admin_settings_entry)


def get_reload_cache_handler() -> CommandHandler:
    return CommandHandler("reload_cache", reload_quran_cache)
