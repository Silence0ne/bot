from __future__ import annotations

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from app.bot.handlers.callbacks import get_callback_handlers
from app.bot.handlers.daily_settings import (
    daily_settings_callback,
    daily_settings,
)
from app.bot.handlers.help import get_handler as get_help_handler
from app.bot.handlers.menu import get_handler as get_main_menu_handler
from app.bot.handlers.random import get_handler as get_random_handler
from app.bot.handlers.random_page import get_handler as get_random_page_handler
from app.bot.handlers.start import get_handler as get_start_handler
from app.bot.handlers.superadmin import (
    admin_settings_entry,
    get_reload_cache_handler,
)
from app.bot.handlers.timezone import get_handler as get_timezone_handler


def register_handlers(application: Application) -> None:
    application.add_handler(get_start_handler())
    application.add_handler(get_help_handler())
    application.add_handler(CommandHandler("superadmin", admin_settings_entry))
    application.add_handler(get_reload_cache_handler())
    application.add_handler(get_random_handler())
    application.add_handler(get_random_page_handler())
    application.add_handler(CommandHandler("dailysettings", daily_settings))
    application.add_handler(get_timezone_handler())
    application.add_handler(get_main_menu_handler())

    # Callback handlers are registered unconditionally. Inline keyboards and
    # callback queries are core to this bot's UX (random ayah/page navigation
    # and the daily-settings wizard), so they must never be silently disabled
    # by a fragile startup capability probe (e.g. on Bale's fork of the Bot
    # API). Each handler is scoped by an explicit pattern so unrelated
    # callbacks are never swallowed.
    for handler in get_callback_handlers():
        application.add_handler(handler)

    # Daily settings wizard callbacks are scoped to their own "daily_" prefix.
    application.add_handler(
        CallbackQueryHandler(
            daily_settings_callback,
            pattern=r"^daily_",
        )
    )
