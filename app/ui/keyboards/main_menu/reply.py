from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup

from app.i18n import get_message


def main_menu_keyboard(language: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(get_message("main_menu_random_button", language))],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
