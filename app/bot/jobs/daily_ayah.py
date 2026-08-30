from __future__ import annotations

import logging
from datetime import time
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from telegram.constants import ParseMode
from telegram.ext import Application, ContextTypes, JobQueue

from app.api.checker import MessengerFeature
from app.bot.handlers.random import format_ayah
from app.core.config import resolve_timezone
from app.i18n import detect_language
from app.ui.keyboards.random import random_ayah_keyboard, random_page_keyboard

if TYPE_CHECKING:
    from app.database.models.chat import Chat

logger = logging.getLogger(__name__)


def _resolve_timezone(chat: "Chat") -> ZoneInfo:
    return resolve_timezone(chat.timezone)


def _parse_daily_time(chat: "Chat") -> time | None:
    try:
        hour_str, minute_str = chat.daily_time.split(":", 1)
        return time(hour=int(hour_str), minute=int(minute_str))
    except (ValueError, AttributeError):
        logger.warning(
            "Invalid daily_time for chat_id=%s: %r",
            chat.chat_id,
            chat.daily_time,
        )
        return None


def _daily_ayah_job_name(chat_id: int) -> str:
    return f"daily_ayah_{chat_id}"


async def send_daily_ayah_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Send the daily ayah to the single user this job was scheduled for.

    Each user gets their own deterministic daily job (see ``schedule_user_daily_ayah``),
    which fires at their exact local time. The ``last_daily_sent_date`` field guards
    against accidental duplicates.
    """
    job = context.job
    if job is None or not isinstance(job.data, dict):
        logger.warning("Daily ayah job invoked without chat_id data")
        return

    chat_id = job.data.get("chat_id")
    if chat_id is None:
        logger.warning("Daily ayah job missing chat_id")
        return

    try:
        from app.core.container import Container
        from app.database.repositories.chat import ChatRepository
        from app.bot.handlers.random_page import format_page, generate_random_page

        container: Container = context.application.bot_data.get("container")
        chat_repo: ChatRepository = context.application.bot_data.get("user_repository")

        if not container or not chat_repo:
            logger.warning("Container or chat repository not available")
            return

        user = await chat_repo.get_by_telegram_id(chat_id)

        if user is None:
            logger.info(
                "User no longer exists, removing daily ayah job: chat_id=%s", chat_id
            )
            remove_daily_ayah_job(context.application, chat_id)
            return

        # Check if user has daily ayah enabled
        if not user.daily_ayah:
            logger.debug(
                "Daily ayah disabled for user: telegram_id=%s",
                user.chat_id,
            )
            return

        # Check if already sent today
        if not await chat_repo.should_send_daily_ayah(user.chat_id):
            logger.debug(
                "Already sent today: telegram_id=%s",
                user.chat_id,
            )
            return

        log_surah: int = -1
        log_ayah: int = -1

        # Determine if sending an ayah or a page
        reply_markup = None

        if user.daily_type == "page":
            # Get random page
            content = await generate_random_page(container)
            # format_page already appends the bot attribution line
            message = format_page(content)

            # Attach the same inline keyboard as the random page
            # (Next Page / Translation toggle).
            if content and context.application.bot_data["feature_checker"].supports(
                MessengerFeature.INLINE_KEYBOARD
            ):
                language = detect_language(user.language)
                reply_markup = random_page_keyboard(
                    content[0].uuid,
                    language,
                    False,
                )
        else:
            # Get random ayah
            ayah = await container.provider.random_ayah()
            log_surah = ayah.surah_number
            log_ayah = ayah.ayah_number
            language = detect_language(user.language)
            # format_ayah already appends the bot attribution line
            message = format_ayah(ayah)

            # Attach the same inline keyboard as the random ayah
            # (Next Ayah).
            if context.application.bot_data["feature_checker"].supports(
                MessengerFeature.INLINE_KEYBOARD
            ):
                reply_markup = random_ayah_keyboard(ayah.uuid, language)

        # Send to user
        await context.bot.send_message(
            chat_id=user.chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )

        # Mark as sent
        await chat_repo.mark_daily_ayah_sent(user.chat_id)

        logger.info(
            "Sent daily ayah: telegram_id=%s, type=%s, surah=%d, ayah=%d",
            user.chat_id,
            user.daily_type,
            log_surah,
            log_ayah,
        )

    except Exception as exc:
        logger.exception(
            "Failed to send daily ayah: telegram_id=%s, error=%s",
            chat_id,
            exc,
        )


def remove_daily_ayah_job(application: Application, chat_id: int) -> None:
    """Cancel any scheduled daily ayah job for the given chat."""
    job_queue: JobQueue | None = application.job_queue
    if job_queue is None:
        return

    name = _daily_ayah_job_name(chat_id)
    for job in job_queue.get_jobs_by_name(name):
        job.schedule_removal()


def schedule_user_daily_ayah(application: Application, chat: "Chat") -> None:
    """
    Schedule a deterministic daily ayah job for a single user.

    The job runs at the user's local time (``chat.daily_time`` in ``chat.timezone``)
    and repeats every day. Any previously scheduled job for the same chat is replaced.
    """
    job_queue: JobQueue | None = application.job_queue
    if job_queue is None:
        return

    remove_daily_ayah_job(application, chat.chat_id)

    if not chat.daily_ayah:
        logger.info("Daily ayah disabled, removing job: chat_id=%s", chat.chat_id)
        return

    tz = _resolve_timezone(chat)
    due_time = _parse_daily_time(chat)
    if due_time is None:
        return

    due_time = due_time.replace(tzinfo=tz)

    job_queue.run_daily(
        send_daily_ayah_job,
        time=due_time,
        days=tuple(range(7)),  # Every day
        name=_daily_ayah_job_name(chat.chat_id),
        data={"chat_id": chat.chat_id},
    )

    logger.info(
        "Scheduled daily ayah: chat_id=%s, time=%s, tz=%s",
        chat.chat_id,
        due_time.strftime("%H:%M"),
        tz.key,
    )


async def schedule_daily_ayah(application: Application) -> None:
    """
    Schedule deterministic daily ayah jobs for all users with daily ayah enabled.

    Called once at startup. Individual users are (re)scheduled as their preferences
    change via ``schedule_user_daily_ayah``.
    """
    container = application.bot_data.get("container")
    chat_repo = application.bot_data.get("user_repository")

    if not container or not chat_repo:
        logger.warning("Container or chat repository not available")
        return

    chats = await chat_repo.list_daily_ayah_enabled()

    for chat in chats:
        schedule_user_daily_ayah(application, chat)

    logger.info("Scheduled daily ayah for %d users", len(chats))
