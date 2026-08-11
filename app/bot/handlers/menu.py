from __future__ import annotations

from collections.abc import Awaitable, Callable

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from app.bot.handlers.random import random_ayah
from app.bot.handlers.superadmin import admin_settings_entry
from app.i18n import SupportedLanguage, detect_language, get_message

MenuAction = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]

# Maps a main-menu button message key to the handler it triggers.
#
# All main-menu buttons share a single MessageHandler (see get_handler()
# below) because Telegram text messages carry no metadata that identifies
# which button was pressed other than their visible text. Registering one
# broad MessageHandler per button would cause the first-registered handler
# to swallow every text update, since python-telegram-bot stops looking for
# further handlers in a group once one handler's filters match.
_MENU_ROUTES: tuple[tuple[str, MenuAction], ...] = (
    ("main_menu_random_button", random_ayah),
)


def _resolve_action(
    text: str,
    language: SupportedLanguage,
) -> MenuAction | None:
    for message_key, action in _MENU_ROUTES:
        if text == get_message(message_key, language):
            return action

    return None


async def dispatch_main_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.message or not update.message.text:
        return

    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    action = _resolve_action(update.message.text, language)

    if action is None:
        return

    await action(update, context)


def get_handler() -> MessageHandler:
    return MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        dispatch_main_menu,
    )
