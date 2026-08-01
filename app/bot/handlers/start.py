from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from app.bot.guards.rate_limit import RateLimitRule, rate_limit
from app.i18n import detect_language, get_message
from app.ui.keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)


@rate_limit(
    RateLimitRule(
        limit=3,
        window_seconds=10,
    )
)
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle /start command.
    
    - Auto-register user to database
    - Set default preferences
    - Enable daily ayah at 3:15 AM
    """
    if not update.message or not update.effective_user:
        return

    telegram_id = update.effective_user.id
    first_name = update.effective_user.first_name or "User"
    username = update.effective_user.username
    last_name = update.effective_user.last_name

    language = detect_language(update.effective_user.language_code)

    try:
        # Get user repository from bot data
        user_repo = context.application.bot_data.get("user_repository")

        if user_repo:
            # Get or create user in database
            user = await user_repo.get_or_create(
                telegram_id=telegram_id,
                first_name=first_name,
                username=username,
                last_name=last_name,
                language=language,
            )

            logger.info(
                "User started: telegram_id=%s, name=%s, daily_ayah_time=%02d:%02d",
                telegram_id,
                first_name,
                user.daily_ayah_hour,
                user.daily_ayah_minute,
            )
        else:
            logger.warning("User repository not available")

        await update.message.reply_text(
            get_message("start", language),
            reply_markup=main_menu_keyboard(language),
        )

    except Exception as exc:
        logger.exception("Start handler failed: error=%s", exc)
        await update.message.reply_text(
            "❌ An error occurred. Please try again."
        )


def get_handler() -> CommandHandler:
    return CommandHandler("start", start)
