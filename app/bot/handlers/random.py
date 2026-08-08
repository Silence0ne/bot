from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from app.api.checker import MessengerFeature
from app.bot.guards.rate_limit import RateLimitRule, rate_limit
from app.core.container import Container
from app.i18n import detect_language, get_message
from app.schemas.ayah import Ayah
from app.ui.keyboards import random_ayah_keyboard

logger = logging.getLogger(__name__)


def format_ayah(ayah: Ayah) -> str:
    surah_line = f"🕋 {ayah.surah_icon} *سوره {ayah.surah_name}*".strip()
    ayah_line = f"📖 *{ayah.text} ﴿{ayah.ayah_number}﴾*"

    translation_line = ""
    if ayah.translation:
        translation_line = f"📝 {ayah.translation} ({ayah.ayah_number})"

    text = f"{surah_line}\n\n{ayah_line}"
    if translation_line:
        text += f"\n\n{translation_line}"

    return f"{text}\n\n@NatiqBot"


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
    if not update.message:
        return

    try:
        container: Container = context.application.bot_data["container"]

        if not container.quran_cache_ready:
            await update.message.reply_text(get_message("random_ayah_error"))
            return

        ayah: Ayah = await container.provider.random_ayah()
        context.user_data["current_ayah_uuid"] = ayah.uuid

        reply_markup = None
        if context.application.bot_data["feature_checker"].supports(
            MessengerFeature.INLINE_KEYBOARD
        ):
            reply_markup = random_ayah_keyboard(ayah.uuid)

        await update.message.reply_text(
            text=format_ayah(ayah),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )

    except Exception as exc:
        logger.exception("Random ayah failed: %s", exc)

        language = detect_language(
            update.effective_user.language_code if update.effective_user else None
        )
        await update.message.reply_text(get_message("random_ayah_error", language))


def get_handler() -> CommandHandler:
    return CommandHandler("random", random_ayah)

