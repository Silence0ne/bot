from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ContextTypes
from zoneinfo import ZoneInfo

from app.bot.guards.rate_limit import RateLimitRule, rate_limit
from app.core.config import get_settings
from app.i18n import detect_language, get_message
from app.ui.keyboards import main_menu_keyboard

if TYPE_CHECKING:
    from app.database.repositories.chat import ChatRepository

logger = logging.getLogger(__name__)

# Timezone data organized by continent
TIMEZONE_CONTINENTS = {
    "Africa": [
        "Africa/Cairo",
        "Africa/Casablanca",
        "Africa/Johannesburg",
        "Africa/Lagos",
        "Africa/Nairobi",
    ],
    "Asia": [
        "Asia/Dubai",
        "Asia/Riyadh",
        "Asia/Tehran",
        "Asia/Karachi",
        "Asia/Dhaka",
        "Asia/Jakarta",
        "Asia/Kolkata",
        "Asia/Tokyo",
        "Asia/Seoul",
        "Asia/Bangkok",
        "Asia/Singapore",
        "Asia/Hong_Kong",
        "Asia/Shanghai",
    ],
    "Europe": [
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Europe/Rome",
        "Europe/Madrid",
        "Europe/Moscow",
        "Europe/Istanbul",
        "Europe/Amsterdam",
        "Europe/Brussels",
        "Europe/Vienna",
    ],
    "America": [
        "America/New_York",
        "America/Los_Angeles",
        "America/Chicago",
        "America/Mexico_City",
        "America/Toronto",
        "America/Bogota",
        "America/Lima",
        "America/Santiago",
        "America/Buenos_Aires",
        "America/Sao_Paulo",
    ],
    "Australia": [
        "Australia/Sydney",
        "Australia/Melbourne",
        "Australia/Brisbane",
        "Australia/Perth",
        "Australia/Adelaide",
    ],
}

# Daily type options
DAILY_TYPES = ["ayah", "page"]


@rate_limit(
    RateLimitRule(
        limit=5,
        window_seconds=60,
    )
)
async def daily_settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle daily sending settings with button-based interface.

    Users can configure:
    1. Timezone (continent → city selection)
    2. Daily sending time (hour/minute buttons)
    3. Daily content type (ayah/page)
    """
    if not update.message or not update.effective_user:
        return

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    try:
        chat_repo: ChatRepository = context.application.bot_data.get("user_repository")

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
                get_message("start", language),
                reply_markup=main_menu_keyboard(language),
            )
            return

        # Show current settings
        current_tz = chat.timezone or get_settings().DAILY_AYAH_DEFAULT_TIMEZONE
        current_time = chat.daily_time or get_settings().DAILY_AYAH_DEFAULT_TIME
        current_type = chat.daily_type or "ayah"

        message = get_message("daily_settings_current", language).format(
            timezone=current_tz,
            time=current_time,
            type=current_type,
        )

        # Create inline keyboard for settings navigation
        keyboard = [
            [
                InlineKeyboardButton(
                    get_message("daily_settings_timezone", language),
                    callback_data="daily_tz_continent",
                ),
                InlineKeyboardButton(
                    get_message("daily_settings_time", language),
                    callback_data="daily_time_hour",
                ),
            ],
            [
                InlineKeyboardButton(
                    get_message("daily_settings_type", language),
                    callback_data="daily_type",
                ),
            ],
            [
                InlineKeyboardButton(
                    get_message("daily_settings_back", language),
                    callback_data="daily_back",
                ),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )

    except Exception as exc:
        logger.exception("Daily settings handler failed: error=%s", exc)
        await update.message.reply_text(
            "❌ An error occurred. Please try again.",
            reply_markup=main_menu_keyboard(language),
        )


async def daily_settings_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle callback queries from daily settings inline keyboard."""
    if not update.callback_query or not update.effective_user:
        return

    await update.callback_query.answer()

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    try:
        chat_repo: ChatRepository = context.application.bot_data.get("user_repository")

        if not chat_repo:
            logger.warning("Chat repository not available")
            await update.callback_query.edit_message_text(
                "Service temporarily unavailable. Please try again.",
                reply_markup=main_menu_keyboard(language),
            )
            return

        telegram_id = update.effective_user.id
        chat = await chat_repo.get_by_telegram_id(telegram_id)

        if not chat:
            await update.callback_query.edit_message_text(
                get_message("start", language),
                reply_markup=main_menu_keyboard(language),
            )
            return

        callback_data = update.callback_query.data

        # Handle different callback actions
        if callback_data == "daily_tz_continent":
            await show_timezone_continents(update, language)
        elif callback_data == "daily_time_hour":
            await show_time_hour_selection(update, language)
        elif callback_data == "daily_type":
            await show_daily_type_selection(update, language)
        elif callback_data == "daily_back":
            await update.callback_query.edit_message_text(
                get_message("daily_settings_current", language).format(
                    timezone=chat.timezone or get_settings().DAILY_AYAH_DEFAULT_TIMEZONE,
                    time=chat.daily_time or get_settings().DAILY_AYAH_DEFAULT_TIME,
                    type=chat.daily_type or "ayah",
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_keyboard(language),
            )
        elif callback_data.startswith("daily_tz_city_"):
            continent = callback_data.replace("daily_tz_city_", "")
            await show_timezone_cities(update, language, continent)
        elif callback_data.startswith("daily_tz_set_"):
            timezone = callback_data.replace("daily_tz_set_", "")
            await set_timezone(update, context, chat_repo, telegram_id, timezone, language)
        elif callback_data.startswith("daily_time_hour_"):
            hour = callback_data.replace("daily_time_hour_", "")
            await show_time_minute_selection(update, language, hour)
        elif callback_data.startswith("daily_time_set_"):
            time = callback_data.replace("daily_time_set_", "")
            await set_time(update, context, chat_repo, telegram_id, time, language)
        elif callback_data.startswith("daily_type_set_"):
            daily_type = callback_data.replace("daily_type_set_", "")
            await set_daily_type(update, context, chat_repo, telegram_id, daily_type, language)

    except Exception as exc:
        logger.exception("Daily settings callback failed: error=%s", exc)
        await update.callback_query.edit_message_text(
            "❌ An error occurred. Please try again.",
            reply_markup=main_menu_keyboard(language),
        )


async def show_timezone_continents(update: Update, language: str) -> None:
    """Show timezone continent selection."""
    keyboard = []
    for continent in TIMEZONE_CONTINENTS.keys():
        keyboard.append([
            InlineKeyboardButton(
                continent,
                callback_data=f"daily_tz_city_{continent}",
            )
        ])
    keyboard.append([
        InlineKeyboardButton(
            get_message("daily_settings_back", language),
            callback_data="daily_back",
        )
    ])

    await update.callback_query.edit_message_text(
        get_message("daily_settings_select_continent", language),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_timezone_cities(
    update: Update,
    language: str,
    continent: str,
) -> None:
    """Show timezone cities for selected continent."""
    cities = TIMEZONE_CONTINENTS.get(continent, [])
    keyboard = []

    # Show cities in rows of 2
    for i in range(0, len(cities), 2):
        row = []
        row.append(
            InlineKeyboardButton(
                cities[i],
                callback_data=f"daily_tz_set_{cities[i]}",
            )
        )
        if i + 1 < len(cities):
            row.append(
                InlineKeyboardButton(
                    cities[i + 1],
                    callback_data=f"daily_tz_set_{cities[i + 1]}",
                )
            )
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(
            get_message("daily_settings_back", language),
            callback_data="daily_tz_continent",
        )
    ])

    await update.callback_query.edit_message_text(
        get_message("daily_settings_select_city", language).format(continent=continent),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def set_timezone(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_repo: ChatRepository,
    telegram_id: int,
    timezone: str,
    language: str,
) -> None:
    """Set user's timezone."""
    try:
        # Validate timezone
        ZoneInfo(timezone)

        await chat_repo.update_preferences(telegram_id=telegram_id, timezone=timezone)

        await update.callback_query.edit_message_text(
            get_message("timezone_set_success", language).format(
                timezone=timezone,
                time=get_settings().DAILY_AYAH_DEFAULT_TIME,
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(language),
        )

        logger.info("User timezone updated: telegram_id=%s, timezone=%s", telegram_id, timezone)

    except Exception as e:
        logger.warning("Invalid timezone: timezone=%s, error=%s", timezone, e)
        await update.callback_query.edit_message_text(
            get_message("timezone_set_error", language),
            reply_markup=main_menu_keyboard(language),
        )


async def show_time_hour_selection(update: Update, language: str) -> None:
    """Show hour selection (0-23)."""
    keyboard = []
    for hour in range(0, 24):
        row = []
        row.append(
            InlineKeyboardButton(
                f"{hour:02d}:00",
                callback_data=f"daily_time_hour_{hour}",
            )
        )
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(
            get_message("daily_settings_back", language),
            callback_data="daily_back",
        )
    ])

    await update.callback_query.edit_message_text(
        get_message("daily_settings_select_hour", language),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_time_minute_selection(
    update: Update,
    language: str,
    hour: str,
) -> None:
    """Show minute selection (0-59 in 15-minute intervals)."""
    keyboard = []
    for minute in [0, 15, 30, 45]:
        row = []
        row.append(
            InlineKeyboardButton(
                f"{hour}:{minute:02d}",
                callback_data=f"daily_time_set_{hour}:{minute:02d}",
            )
        )
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(
            get_message("daily_settings_back", language),
            callback_data="daily_time_hour",
        )
    ])

    await update.callback_query.edit_message_text(
        get_message("daily_settings_select_minute", language).format(hour=hour),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def set_time(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_repo: ChatRepository,
    telegram_id: int,
    time: str,
    language: str,
) -> None:
    """Set user's daily sending time."""
    try:
        await chat_repo.update_preferences(telegram_id=telegram_id, daily_time=time)

        await update.callback_query.edit_message_text(
            get_message("time_set_success", language).format(time=time),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(language),
        )

        logger.info("User daily time updated: telegram_id=%s, time=%s", telegram_id, time)

    except Exception as e:
        logger.exception("Failed to set time: time=%s, error=%s", time, e)
        await update.callback_query.edit_message_text(
            get_message("time_set_error", language),
            reply_markup=main_menu_keyboard(language),
        )


async def show_daily_type_selection(update: Update, language: str) -> None:
    """Show daily content type selection (ayah/page)."""
    keyboard = [
        [
            InlineKeyboardButton(
                get_message("daily_type_ayah", language),
                callback_data="daily_type_set_ayah",
            ),
            InlineKeyboardButton(
                get_message("daily_type_page", language),
                callback_data="daily_type_set_page",
            ),
        ],
        [
            InlineKeyboardButton(
                get_message("daily_settings_back", language),
                callback_data="daily_back",
            )
        ],
    ]

    await update.callback_query.edit_message_text(
        get_message("daily_settings_select_type", language),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def set_daily_type(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_repo: ChatRepository,
    telegram_id: int,
    daily_type: str,
    language: str,
) -> None:
    """Set user's daily content type."""
    try:
        await chat_repo.update_preferences(telegram_id=telegram_id, daily_type=daily_type)

        await update.callback_query.edit_message_text(
            get_message("daily_type_set_success", language).format(type=daily_type),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(language),
        )

        logger.info("User daily type updated: telegram_id=%s, type=%s", telegram_id, daily_type)

    except Exception as e:
        logger.exception("Failed to set daily type: type=%s, error=%s", daily_type, e)
        await update.callback_query.edit_message_text(
            get_message("daily_type_set_error", language),
            reply_markup=main_menu_keyboard(language),
        )
