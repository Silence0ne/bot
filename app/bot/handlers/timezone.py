from __future__ import annotations

import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes
from zoneinfo import ZoneInfo

from app.bot.guards.rate_limit import RateLimitRule, rate_limit
from app.core.config import get_settings
from app.core.container import Container
from app.i18n import detect_language, get_message
from app.ui.keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)

# Common timezone options for users
COMMON_TIMEZONES = [
    "Asia/Dubai",
    "Asia/Riyadh", 
    "Asia/Tehran",
    "Europe/London",
    "America/New_York",
    "America/Los_Angeles",
    "Asia/Kolkata",
    "Asia/Tokyo",
    "Australia/Sydney",
]


@rate_limit(
    RateLimitRule(
        limit=3,
        window_seconds=30,
    )
)
async def timezone_settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle timezone settings via menu button or direct command.
    
    Users can:
    1. Select from common timezones
    2. Type their own timezone in Region/City format
    3. View their current timezone setting
    """
    if not update.message or not update.effective_user:
        return

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    try:
        chat_repo = context.application.bot_data.get("user_repository")
        
        if not chat_repo:
            logger.warning("Chat repository not available")
            await update.message.reply_text(
                "Service temporarily unavailable. Please try again.",
                reply_markup=main_menu_keyboard(language),
            )
            return
        
        telegram_id = update.effective_user.id
        chat = await chat_repo.get_by_telegram_id(telegram_id)
        
        if not chat:
            await update.message.reply_text(
                "Please start the bot first with /start",
                reply_markup=main_menu_keyboard(language),
            )
            return

        # Check if user sent a timezone
        text = update.message.text.strip()
        
        # Check if it's one of the common timezones or a valid timezone
        if text and text != get_message("main_menu_timezone_button", language):
            # Try to set the timezone
            try:
                # Validate timezone
                test_tz = ZoneInfo(text)
                current_time = datetime.now(test_tz).strftime("%H:%M")
                
                # Update user's timezone
                await chat_repo.update_preferences(
                    telegram_id=telegram_id,
                    timezone=text,
                )
                
                await update.message.reply_text(
                    get_message("timezone_set_success", language).format(
                        timezone=text,
                        time=current_time
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=main_menu_keyboard(language),
                )
                logger.info("User timezone updated: telegram_id=%s, timezone=%s", telegram_id, text)
                return
                
            except Exception as e:
                logger.warning("Invalid timezone: telegram_id=%s, timezone=%s, error=%s", telegram_id, text, e)
                await update.message.reply_text(
                    get_message("timezone_set_error", language),
                    reply_markup=main_menu_keyboard(language),
                )
                return

        # Show current timezone and options
        current_tz = chat.timezone or get_settings().DAILY_AYAH_DEFAULT_TIMEZONE
        current_time_str = chat.daily_time or get_settings().DAILY_AYAH_DEFAULT_TIME
        
        try:
            current_tz_obj = ZoneInfo(current_tz)
            current_local_time = datetime.now(current_tz_obj).strftime("%H:%M")
        except:
            current_local_time = current_time_str

        message = get_message("timezone_current", language).format(
            timezone=current_tz,
            time=current_local_time
        )
        
        message += f"\n\n{get_message('timezone_prompt', language)}"

        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(language),
        )

    except Exception as exc:
        logger.exception("Timezone handler failed: error=%s", exc)
        await update.message.reply_text("❌ An error occurred. Please try again.")


def get_handler() -> CommandHandler:
    return CommandHandler("timezone", timezone_settings)