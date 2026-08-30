from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ContextTypes

from app.api.checker import MessengerFeature
from app.bot.handlers.random import format_ayah
from app.bot.handlers.random_page import format_page, generate_random_page
from app.core.container import Container
from app.i18n import detect_language, get_message
from app.schemas.ayah import Ayah
from app.ui.keyboards.random import random_ayah_keyboard, random_page_keyboard

logger = logging.getLogger(__name__)


async def _reply_with_ayah(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    ayah: Ayah,
) -> None:
    query = update.callback_query

    if query is None:
        return

    message = query.message

    if message is None:
        return

    context.user_data["current_ayah_uuid"] = ayah.uuid

    reply_markup = None

    # Build and pass language to keyboard builder
    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    if context.application.bot_data["feature_checker"].supports(
        MessengerFeature.INLINE_KEYBOARD
    ):
        reply_markup = random_ayah_keyboard(ayah.uuid, language)

    # Send as new message
    await message.reply_text(
        text=format_ayah(ayah),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
    )


async def _reply_with_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    ayahs: list[Ayah],
) -> None:
    query = update.callback_query

    if query is None:
        return

    message = query.message

    if message is None:
        return

    reply_markup = None

    # Build and pass language to keyboard builder
    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    # Check translation state
    show_translation = context.user_data.get("show_translation", False)

    if (
        context.application.bot_data["feature_checker"].supports(
            MessengerFeature.INLINE_KEYBOARD
        )
        and ayahs
    ):
        reply_markup = random_page_keyboard(ayahs[0].uuid, language, show_translation)

    # Send as new message
    await message.reply_text(
        text=format_page(ayahs),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
    )


async def _handle_next_ayah(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    try:
        container: Container = context.application.bot_data["container"]
        # current_uuid is now extracted directly from query data to ensure uniqueness

        if not container.quran_cache_ready:
            await query.answer(
                get_message("next_ayah_error"),
                show_alert=True,
            )
            return

        ayah: Ayah = await container.provider.next_ayah(
            current_uuid=query.data.split(":")[1],
        )

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

        await _reply_with_ayah(
            update,
            context,
            ayah,
        )

    except Exception:
        logger.exception("Next ayah callback failed")
        await query.answer(
            get_message("next_ayah_error"),
            show_alert=True,
        )


async def random_ayah_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    try:
        container: Container = context.application.bot_data["container"]

        if not container.quran_cache_ready:
            await query.answer(
                get_message("next_ayah_error"),
                show_alert=True,
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

        await _reply_with_ayah(
            update,
            context,
            ayah,
        )

    except Exception:
        logger.exception("Random ayah callback failed")
        await query.answer(
            get_message("next_ayah_error"),
            show_alert=True,
        )


async def _handle_next_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    try:
        container: Container = context.application.bot_data["container"]

        if not container.quran_cache_ready:
            await query.answer(
                get_message("random_page_error"),
                show_alert=True,
            )
            return

        # Determine the current page from the uuid in the callback data.
        # user_data["current_page"] is only set for pages generated interactively,
        # so it cannot be relied on here (e.g. daily-sent pages never set it).
        current_ayahs = await container.provider.get_ayahs_by_first_ayah_uuid(
            query.data.split(":")[1]
        )
        current_page = (
            current_ayahs[0].page
            if current_ayahs and current_ayahs[0].page is not None
            else (context.user_data.get("current_page") or 1)
        )
        next_page = current_page + 1

        # Get ayahs for the next page
        page_ayahs = await container.provider.get_ayahs_by_page(next_page)

        # If no ayahs found for this page, fall back to a random page
        if not page_ayahs:
            page_ayahs = await generate_random_page(container)
            if page_ayahs:
                context.user_data["current_page"] = page_ayahs[0].page
        else:
            # Update current page in user data
            context.user_data["current_page"] = next_page

        # Track in database
        if update.effective_user and page_ayahs:
            chat = await container.chat_repository.get_by_telegram_id(
                update.effective_user.id
            )
            if chat:
                await container.sent_history_repository.log_sent(
                    chat_uuid=chat.uuid,
                    ayah_uuid=page_ayahs[0].uuid,
                    reading_mode="page",
                )

        # Check if user previously chose to see translations
        show_translation = context.user_data.get("show_translation", False)

        if show_translation:
            await _reply_with_page_translation(
                update,
                context,
                page_ayahs,
            )
        else:
            await _reply_with_page(
                update,
                context,
                page_ayahs,
            )

    except Exception:
        logger.exception("Next page callback failed")
        await query.answer(
            get_message("random_page_error"),
            show_alert=True,
        )


async def _handle_page_translation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    try:
        container: Container = context.application.bot_data["container"]

        if not container.quran_cache_ready:
            await query.answer(
                get_message("random_page_error"),
                show_alert=True,
            )
            return

        # Set translation state for this user
        context.user_data["show_translation"] = True

        # Re-render the SAME page currently on screen with translations,
        # instead of generating a brand-new random page.
        first_ayah_uuid = query.data.split(":")[1]
        page_ayahs = await container.provider.get_ayahs_by_first_ayah_uuid(
            first_ayah_uuid
        )

        if not page_ayahs:
            page_ayahs = await generate_random_page(container)

        if page_ayahs:
            context.user_data["current_page"] = page_ayahs[0].page

        # Track in database
        if update.effective_user and page_ayahs:
            chat = await container.chat_repository.get_by_telegram_id(
                update.effective_user.id
            )
            if chat:
                await container.sent_history_repository.log_sent(
                    chat_uuid=chat.uuid,
                    ayah_uuid=page_ayahs[0].uuid,
                    reading_mode="page",
                )

        await _reply_with_page_translation(
            update,
            context,
            page_ayahs,
        )

    except Exception:
        logger.exception("Page translation callback failed")
        await query.answer(
            get_message("random_page_error"),
            show_alert=True,
        )


async def _handle_page_no_translation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    try:
        container: Container = context.application.bot_data["container"]

        if not container.quran_cache_ready:
            await query.answer(
                get_message("random_page_error"),
                show_alert=True,
            )
            return

        # Reset translation state for this user
        context.user_data["show_translation"] = False

        # Re-render the SAME page currently on screen without translations,
        # instead of generating a brand-new random page.
        first_ayah_uuid = query.data.split(":")[1]
        page_ayahs = await container.provider.get_ayahs_by_first_ayah_uuid(
            first_ayah_uuid
        )

        if not page_ayahs:
            page_ayahs = await generate_random_page(container)

        if page_ayahs:
            context.user_data["current_page"] = page_ayahs[0].page

        # Track in database
        if update.effective_user and page_ayahs:
            chat = await container.chat_repository.get_by_telegram_id(
                update.effective_user.id
            )
            if chat:
                await container.sent_history_repository.log_sent(
                    chat_uuid=chat.uuid,
                    ayah_uuid=page_ayahs[0].uuid,
                    reading_mode="page",
                )

        await _reply_with_page(
            update,
            context,
            page_ayahs,
        )

    except Exception:
        logger.exception("Page no translation callback failed")
        await query.answer(
            get_message("random_page_error"),
            show_alert=True,
        )


async def _reply_with_page_translation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    ayahs: list[Ayah],
) -> None:
    query = update.callback_query

    if query is None:
        return

    message = query.message

    if message is None:
        return

    reply_markup = None

    # Build and pass language to keyboard builder
    language = detect_language(
        update.effective_user.language_code if update.effective_user else None
    )

    if (
        context.application.bot_data["feature_checker"].supports(
            MessengerFeature.INLINE_KEYBOARD
        )
        and ayahs
    ):
        reply_markup = random_page_keyboard(ayahs[0].uuid, language, True)

    # Send as new message
    await message.reply_text(
        text=format_page(ayahs, show_translation=True),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
    )


def get_callback_handlers() -> list[CallbackQueryHandler]:
    return [
        CallbackQueryHandler(
            random_ayah_callback,
            pattern=r"^random_ayah$",
        ),
        CallbackQueryHandler(
            _handle_next_ayah,
            pattern=r"^next_ayah:",
        ),
        CallbackQueryHandler(
            _handle_next_page,
            pattern=r"^next_page:",
        ),
        CallbackQueryHandler(
            _handle_page_translation,
            pattern=r"^page_translation:",
        ),
        CallbackQueryHandler(
            _handle_page_no_translation,
            pattern=r"^page_no_translation:",
        ),
    ]
