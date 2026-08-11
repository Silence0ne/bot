from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup

from app.i18n import get_message


def main_menu_keyboard(language: str, is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(get_message("main_menu_random_button", language))],
    ]
    if is_admin:
        buttons.append(
            [KeyboardButton(get_message("main_menu_admin_button", language))]
        )

    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
        one_time_keyboard=False,
    )
