from __future__ import annotations

import logging
import shutil
from typing import TYPE_CHECKING, Protocol

import psutil
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from app.bot.guards.rate_limit import RateLimitRule, rate_limit
from app.core.config import get_settings
from app.core.markdown import format_markdown_v2
from app.i18n import detect_language, get_message
from app.ui.keyboards import main_menu_keyboard

if TYPE_CHECKING:
    pass

if TYPE_CHECKING:
    from app.database.models.chat import Chat

logger = logging.getLogger(__name__)


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

    try:
        chat = await chat_repository.get_by_telegram_id(telegram_id)
        if chat is None:
            return False

        # Check if is_admin attribute exists (for database compatibility)
        if hasattr(chat, "is_admin"):
            return chat.is_admin

        return False
    except Exception as e:
        logger.warning(
            "Error checking admin status in database: telegram_id=%s, error=%s",
            telegram_id,
            e,
        )
        return False


async def _is_superadmin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    user = update.effective_user

    if user is None or user.id is None:
        return False

    settings = get_settings()
    container = context.application.bot_data.get("container")

    if not container:
        return False

    return await _resolve_is_superadmin(
        user.id,
        configured_admin_ids=settings.admin_user_ids,
        chat_repository=container.chat_repository,
    )


async def _get_system_stats(context: ContextTypes.DEFAULT_TYPE) -> str:
    cpu_usage = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    disk = shutil.disk_usage("/")

    container = context.application.bot_data.get("container")
    if container:
        user_counts = await container.chat_repository.count_by_type()
        total_users = sum(user_counts.values())
    else:
        total_users = 0

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
    container = context.application.bot_data.get("container")

    # Admin list (env)
    admin_list = ", ".join(map(str, sorted(settings.admin_user_ids)))

    # Categorized Admin Dashboard
    env_info = (
        f"🌐 Platform: {settings.PLATFORM}\n"
        f"🌍 Language: {settings.BOT_LANGUAGE}\n"
        f"🔐 Admins: {admin_list}\n"
        f"🔑 API Key (Set: {'✅' if settings.BOT_TOKEN else '❌'})\n"
        f"⏱ API Timeout: {settings.NATIQ_API_TIMEOUT}s"
    )

    bot_api_info = (
        f"📍 Base URL: {settings.BOT_API}\n"
        f"🌐 Natiq API: {settings.NATIQ_API_URL}\n"
        f"🗝 Token masked: {settings.BOT_TOKEN[:4]}...{settings.BOT_TOKEN[-4:] if len(settings.BOT_TOKEN) > 8 else '***'}"
    )

    # Helper to get cache icon
    def _get_cache_icon() -> str:
        if container and container.loader.loading:
            return "🔄"
        return "✅" if container and container.quran_cache_ready else "❌"

    return get_message("admin_dashboard", language).format(
        stats=stats,
        env_info=env_info,
        bot_api_info=bot_api_info,
        total_ayahs=totals["ayahs"],
        total_pages=totals["pages"],
        quran_cache_ready=_get_cache_icon(),
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

    user_id = update.effective_user.id if update.effective_user else "unknown"
    settings = get_settings()
    message = get_message("admin_access_denied", language).format(user_id=user_id)

    await update.message.reply_text(
        f"{message}\n\n📱 {settings.BOT_USERNAME}",
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

    container = context.application.bot_data.get("container")
    if not container:
        settings = get_settings()
        await update.message.reply_text(
            f"Service temporarily unavailable. Please try again.\n\n📱 {settings.BOT_USERNAME}",
            reply_markup=main_menu_keyboard(language),
        )
        return

    settings = get_settings()
    await update.message.reply_text(
        f"{get_message('admin_cache_reloading', language)}\n\n📱 {settings.BOT_USERNAME}"
    )

    reloaded = await container.reload_quran_cache()

    result_key = (
        "admin_cache_reload_success" if reloaded else "admin_cache_reload_failed"
    )
    settings = get_settings()

    await update.message.reply_text(
        f"{get_message(result_key, language)}\n\n📱 {settings.BOT_USERNAME}",
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

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    if not await _is_superadmin(update, context):
        await _reply_admin_denied(update, context)
        return

    container = context.application.bot_data.get("container")
    if not container:
        settings = get_settings()
        await update.message.reply_text(
            f"Service temporarily unavailable. Please try again.\n\n📱 {settings.BOT_USERNAME}",
            reply_markup=main_menu_keyboard(language),
        )
        return

    stats = await _get_system_stats(context)
    totals = await container.chat_repository.get_send_totals()
    settings = get_settings()

    await update.message.reply_text(
        format_markdown_v2(
            f"{_build_admin_dashboard(update, context, language, stats, totals)}\n\n📱 {settings.BOT_USERNAME}"
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=main_menu_keyboard(language),
    )


def get_command_handler() -> CommandHandler:
    return CommandHandler("superadmin", admin_settings_entry)


def get_reload_cache_handler() -> CommandHandler:
    return CommandHandler("reload_cache", reload_quran_cache)
