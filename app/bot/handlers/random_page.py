from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from app.api.checker import MessengerFeature
from app.bot.guards.rate_limit import RateLimitRule, rate_limit
from app.core.config import get_settings
from app.i18n import detect_language, get_message
from app.schemas.ayah import Ayah
from app.ui.keyboards.random import random_page_keyboard

if TYPE_CHECKING:
    from app.core.container import Container

logger = logging.getLogger(__name__)


async def generate_random_page(container: Container) -> list[Ayah]:
    """Generate a random page by selecting a random Quran page."""
    return await container.provider.random_page()


def format_page(
    ayahs: list[Ayah],
    *,
    show_translation: bool = False,
) -> str:
    """Format a page (group of ayahs), optionally including translations."""
    settings = get_settings()
    parts: list[str] = []

    # Surah header
    if ayahs:
        first_ayah = ayahs[0]
        page_num = first_ayah.page if first_ayah.page else "?"
        icon = first_ayah.surah_icon if first_ayah.surah_icon else "🕋"
        parts.append(f"{icon} *{first_ayah.surah_name}* (Page {page_num})")

        if show_translation:
            if first_ayah.show_bismillah_line and first_ayah.bismillah_text:
                parts.append(first_ayah.bismillah_text)
            parts.append("")
        else:
            parts.append("")

    # Format each ayah in the page with better spacing
    for i, ayah in enumerate(ayahs):
        if show_translation and i > 0:
            parts.append("─" * 10)

        parts.append(f"📖 *{ayah.text} ﴿{ayah.ayah_number}﴾*")

        if show_translation:
            if ayah.translation:
                parts.append(f"📝 {ayah.translation}")
        else:
            parts.append("──────────")

    # Remove the last separator
    if not show_translation and parts:
        parts.pop()

    # Attribution
    parts.append("")
    parts.append(f"📱 {settings.BOT_USERNAME}")

    return "\n".join(parts)


@rate_limit(
    RateLimitRule(
        limit=3,
        window_seconds=30,
    )
)
async def random_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Send a random Quran page (group of ayahs)."""
    if not update.message:
        return

    try:
        container = context.application.bot_data.get("container")

        if not container:
            logger.warning("Container not available")
            settings = get_settings()
            await update.message.reply_text(
                f"{get_message('random_page_error')}\n\n📱 {settings.BOT_USERNAME}"
            )
            return

        if not container.quran_cache_ready:
            settings = get_settings()
            await update.message.reply_text(
                f"{get_message('random_page_loading')}\n\n📱 {settings.BOT_USERNAME}"
            )
            return

        # Generate random page
        page_ayahs = await generate_random_page(container)

        # Reset translation state for new random page
        context.user_data["show_translation"] = False

        # Store current page number for next page navigation
        if page_ayahs:
            context.user_data["current_page"] = page_ayahs[0].page

        # Track in database
        if update.effective_user and page_ayahs:
            chat = await container.chat_repository.get_by_telegram_id(
                update.effective_user.id
            )
            if chat:
                # Log the first ayah as representative of the page
                await container.sent_history_repository.log_sent(
                    chat_uuid=chat.uuid,
                    ayah_uuid=page_ayahs[0].uuid,
                    reading_mode="page",
                )

        # Pass the correct language
        language = detect_language(
            update.effective_user.language_code if update.effective_user else None
        )

        reply_markup = None
        if (
            context.application.bot_data["feature_checker"].supports(
                MessengerFeature.INLINE_KEYBOARD
            )
            and page_ayahs
        ):
            show_translation = context.user_data.get("show_translation", False)
            reply_markup = random_page_keyboard(
                page_ayahs[0].uuid, language, show_translation
            )

        await update.message.reply_text(
            text=format_page(page_ayahs),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )

    except Exception as exc:
        logger.exception("Random page failed: %s", exc)
        settings = get_settings()
        await update.message.reply_text(
            f"{get_message('random_page_error')}\n\n📱 {settings.BOT_USERNAME}"
        )


def get_handler() -> CommandHandler:
    return CommandHandler("randompage", random_page)
