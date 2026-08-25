from __future__ import annotations

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.i18n import get_message


def random_ayah_keyboard(
    ayah_uuid: str,
    language: str,
) -> InlineKeyboardMarkup:
    """
    Keyboard for ayah navigation.

    Callback format:

        next_ayah:{ayah_uuid}

    The callback handler uses this UUID
    to locate the current ayah.
    """

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=get_message(
                        "next_ayah_button",
                        language,
                    ),
                    callback_data=f"next_ayah:{ayah_uuid}",
                ),
            ],
        ]
    )


def random_page_keyboard(
    ayah_uuid: str,
    language: str,
    show_translation: bool = False,
) -> InlineKeyboardMarkup:
    """
    Keyboard for page navigation.

    Callback format:

        next_page:{ayah_uuid}
        page_translation:{ayah_uuid}
        page_no_translation:{ayah_uuid}

    The callback handler uses this UUID
    to locate the current page (first ayah).
    """

    if show_translation:
        # Show "Without Translation" button when currently showing translations
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=get_message(
                            "next_page_button",
                            language,
                        ),
                        callback_data=f"next_page:{ayah_uuid}",
                    ),
                    InlineKeyboardButton(
                        text=get_message(
                            "page_no_translation_button",
                            language,
                        ),
                        callback_data=f"page_no_translation:{ayah_uuid}",
                    ),
                ],
            ]
        )
    else:
        # Show "Translation" button when not currently showing translations
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=get_message(
                            "next_page_button",
                            language,
                        ),
                        callback_data=f"next_page:{ayah_uuid}",
                    ),
                    InlineKeyboardButton(
                        text=get_message(
                            "page_translation_button",
                            language,
                        ),
                        callback_data=f"page_translation:{ayah_uuid}",
                    ),
                ],
            ]
        )
