from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from app.api.checker import MessengerFeature
from app.bot.guards.rate_limit import RateLimitRule, rate_limit
from app.core.config import get_settings
from app.i18n import detect_language, get_message
from app.schemas.ayah import Ayah
from app.ui.keyboards import random_ayah_keyboard

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def format_page(ayahs: list[Ayah]) -> str:
    """Format a page (group of ayahs) in a language-agnostic way."""
    settings = get_settings()
    parts: list[str] = []

    # Surah header
    if ayahs:
        first_ayah = ayahs[0]
        if first_ayah.surah_icon:
            parts.append(f"{first_ayah.surah_icon} *{first_ayah.surah_name}*")
        else:
            parts.append(f"*{first_ayah.surah_name}*")

        # Bismillah (shown before the first ayah when applicable)
        if first_ayah.show_bismillah_line and first_ayah.bismillah_text:
            parts.append(first_ayah.bismillah_text)

    # Format each ayah in the page
    for ayah in ayahs:
        parts.append(f"📖 *{ayah.text} ﴿{ayah.ayah_number}﴾*")

    # Attribution
    parts.append(settings.BOT_USERNAME)

    return "\n\n".join(parts)


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
            await update.message.reply_text(get_message("random_page_error"))
            return

        if not container.quran_cache_ready:
            await update.message.reply_text(get_message("random_page_loading"))
            return

        # Get multiple random ayahs to form a "page" (typically 10-15 ayahs)
        # Since the API doesn't have a specific page endpoint, we'll get random ayahs
        ayah_count = random.randint(10, 15)
        page_ayahs: list[Ayah] = []

        for _ in range(ayah_count):
            ayah: Ayah = await container.provider.random_ayah()
            page_ayahs.append(ayah)

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
        if context.application.bot_data["feature_checker"].supports(
            MessengerFeature.INLINE_KEYBOARD
        ) and page_ayahs:
            reply_markup = random_ayah_keyboard(page_ayahs[0].uuid, language)

        await update.message.reply_text(
            text=format_page(page_ayahs),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )

    except Exception as exc:
        logger.exception("Random page failed: %s", exc)
        await update.message.reply_text(get_message("random_page_error"))


def get_handler() -> CommandHandler:
    return CommandHandler("randompage", random_page)
