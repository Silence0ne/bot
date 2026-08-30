from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from app.api.checker import MessengerFeature
from app.bot.guards.rate_limit import RateLimitRule, rate_limit
from app.core.config import get_settings
from app.core.markdown import escape_html
from app.i18n import detect_language, get_message
from app.schemas.ayah import Ayah
from app.ui.keyboards import random_ayah_keyboard

logger = logging.getLogger(__name__)


def format_ayah(ayah: Ayah) -> str:
    """Format ayah in a language-agnostic way."""
    settings = get_settings()
    parts: list[str] = []

    # Surah header: makki/madani icon + surah name (no trailing space if no icon)
    surah_name = escape_html(ayah.surah_name)
    if ayah.surah_icon:
        parts.append(f"{ayah.surah_icon} <b>{surah_name}</b>")
    else:
        parts.append(f"<b>{surah_name}</b>")

    # Bismillah (shown before the ayah text when applicable)
    if ayah.show_bismillah_line and ayah.bismillah_text:
        parts.append(escape_html(ayah.bismillah_text))

    # Ayah text
    ayah_text = escape_html(f"{ayah.text} ﴿{ayah.ayah_number}﴾")
    parts.append(f"📖 <b>{ayah_text}</b>")

    # Translation (if available)
    if ayah.translation:
        parts.append(f"📝 {escape_html(ayah.translation)} ({ayah.ayah_number})")

    # Attribution
    parts.append(f"📱 {escape_html(settings.BOT_USERNAME)}")

    return "\n\n".join(parts)


@rate_limit(
    RateLimitRule(
        limit=5,
        window_seconds=15,
    )
)
async def random_ayah(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Send a random Quran ayah."""
    if not update.message:
        return

    try:
        container = context.application.bot_data.get("container")

        if not container:
            logger.warning("Container not available")
            settings = get_settings()
            await update.message.reply_text(
                f"{get_message('random_ayah_error')}\n\n📱 {settings.BOT_USERNAME}"
            )
            return

        if not container.quran_cache_ready:
            settings = get_settings()
            await update.message.reply_text(
                f"{get_message('random_ayah_error')}\n\n📱 {settings.BOT_USERNAME}"
            )
            return

        ayah: Ayah = await container.provider.random_ayah()

        # Track in database
        if update.effective_user:
            chat = await container.chat_repository.get_by_telegram_id(
                update.effective_user.id
            )
            if chat:
                await container.sent_history_repository.log_sent(
                    chat_uuid=chat.uuid,
                    ayah_uuid=ayah.uuid,
                    reading_mode="ayah",
                )

        # Pass the correct language
        language = detect_language(
            update.effective_user.language_code if update.effective_user else None
        )

        reply_markup = None
        if context.application.bot_data["feature_checker"].supports(
            MessengerFeature.INLINE_KEYBOARD
        ):
            reply_markup = random_ayah_keyboard(ayah.uuid, language)

        await update.message.reply_text(
            text=format_ayah(ayah),
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )

    except Exception as exc:
        logger.exception("Random ayah failed: %s", exc)
        settings = get_settings()
        await update.message.reply_text(
            f"{get_message('random_ayah_error')}\n\n📱 {settings.BOT_USERNAME}"
        )


def get_handler() -> CommandHandler:
    return CommandHandler("random", random_ayah)
