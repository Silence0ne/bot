from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Protocol

import psutil
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from app.bot.guards.rate_limit import RateLimitRule, rate_limit
from app.core.config import get_settings
from app.core.container import Container
from app.i18n import detect_language, get_message
from app.ui.keyboards import main_menu_keyboard

if TYPE_CHECKING:
    from app.database.models.chat import Chat


class SupportsAdminLookup(Protocol):
    async def get_by_telegram_id(self, telegram_id: int) -> "Chat | None": ...


async def _resolve_is_superadmin(
    telegram_id: int,
    *,
    configured_admin_ids: set[int],
    chat_repository: SupportsAdminLookup,
) -> bool:
    """
    A user is an admin if either is true:

    - their numeric ID is listed in the `ADMIN_USER_IDS` setting, or
    - their `chats.is_admin` database column is set to true.

    The env-based check is tried first since it never requires a
    database round-trip.
    """
    if telegram_id in configured_admin_ids:
        return True

    chat = await chat_repository.get_by_telegram_id(telegram_id)
    return chat is not None and chat.is_admin


async def _is_superadmin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    user = update.effective_user

    if user is None or user.id is None:
        return False

    settings = get_settings()
    container: Container = context.application.bot_data["container"]

    return await _resolve_is_superadmin(
        user.id,
        configured_admin_ids=settings.admin_user_ids,
        chat_repository=container.chat_repository,  # <-- Changed here
    )


async def _get_system_stats(context: ContextTypes.DEFAULT_TYPE) -> str:
    cpu_usage = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    disk = shutil.disk_usage("/")

    container: Container = context.application.bot_data["container"]
    user_counts = await container.chat_repository.count_by_type()
    total_users = sum(user_counts.values())

    return (
        f"🖥 CPU: {cpu_usage}%\n"
        f"💾 RAM: {ram.percent}% ({ram.used // 1024**2}MB / {ram.total // 1024**2}MB)\n"
        f"💽 Disk: {(disk.used / disk.total) * 100:.1f}% ({disk.used // 1024**3}GB / {disk.total // 1024**3}GB)\n"
        f"👥 Total Users: {total_users}"
    )


def _build_admin_dashboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    language: str,
    stats: str,
    totals: dict[str, int],
) -> str:
    settings = get_settings()
    container: Container = context.application.bot_data["container"]

    # Extract key env settings
    env_info = (
        f"🌐 Platform: {settings.PLATFORM}\n"
        f"🏷 App Name: {settings.APP_NAME}\n"
        f"🌍 Language: {settings.BOT_LANGUAGE}\n"
        f"⏱ API Timeout: {settings.NATIQ_API_TIMEOUT}s"
    )

    return get_message("admin_dashboard", language).format(
        stats=stats,
        env_info=env_info,
        total_ayahs=totals["ayahs"],
        total_pages=totals["pages"],
        quran_cache_ready="✅" if container.quran_cache_ready else "❌",
        bot_id=context.bot.id,
        bot_language=settings.BOT_LANGUAGE,
        api_status="✅",
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

    if not await _is_superadmin(update, context):
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

    if not await _is_superadmin(update, context):
        await _reply_admin_denied(update, context)
        return

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    container: Container = context.application.bot_data["container"]
    stats = await _get_system_stats(context)
    totals = await container.chat_repository.get_send_totals()

    await update.message.reply_text(
        _build_admin_dashboard(update, context, language, stats, totals),
        reply_markup=main_menu_keyboard(language),
    )


def get_command_handler() -> CommandHandler:
    return CommandHandler("superadmin", admin_settings_entry)


def get_reload_cache_handler() -> CommandHandler:
    return CommandHandler("reload_cache", reload_quran_cache)
