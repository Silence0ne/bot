from __future__ import annotations

import logging
from datetime import datetime, timezone

from telegram.ext import Application, JobQueue

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def send_daily_ayah_job(context) -> None:
    """
    Send daily ayah to users at their scheduled time.

    The job runs in UTC (hardcoded Greenwich) at 00:00 and checks users' local timezones
    to determine if it's their scheduled time for daily ayah delivery.

    System:
    1. Hardcoded base: UTC (Greenwich) at 00:00
    2. Environment config: Default timezone (Asia/Riyadh) and time (03:15)
    3. User-specific: Users can set their own timezone via bot interaction
    """
    try:
        from app.core.container import Container
        from app.database.repositories.chat import ChatRepository
        from app.bot.handlers.random_page import format_page, generate_random_page

        container: Container = context.application.bot_data.get("container")
        chat_repo: ChatRepository = context.application.bot_data.get("user_repository")

        if not container or not chat_repo:
            logger.warning("Container or chat repository not available")
            return

        # Run in UTC (hardcoded Greenwich)
        now = datetime.now(timezone.utc)
        hour = now.hour
        minute = now.minute

        logger.info(
            "Running daily ayah job (UTC): %02d:%02d",
            hour,
            minute,
        )

        # Get all users who should receive ayah at this time (based on their timezone)
        users = await chat_repo.list_due_for_daily_ayah()

        if not users:
            logger.info("No users scheduled for current time")
            return

        logger.info("Sending daily ayah to %d users", len(users))

        for user in users:
            try:
                # Check if user has daily ayah enabled
                if not user.daily_ayah:
                    logger.debug(
                        "Daily ayah disabled for user: telegram_id=%s",
                        user.chat_id,
                    )
                    continue

                # Check if already sent today
                should_send = await chat_repo.should_send_daily_ayah(user.chat_id)

                if not should_send:
                    logger.debug(
                        "Already sent today: telegram_id=%s",
                        user.chat_id,
                    )
                    continue

                # Get settings instance
                settings = get_settings()

                # Determine if sending an ayah or a page
                if user.daily_type == "page":
                    # Get random page
                    content = await generate_random_page(container)
                    # Use format_page from app.bot.handlers.random_page
                    message = format_page(content)
                    message += f"\n\n📱 {settings.BOT_USERNAME}"
                else:
                    # Get random ayah
                    ayah = await container.provider.random_ayah()
                    # Format message
                    message = (
                        f"🕋 *{ayah.surah_name}*\n\n"
                        f"📖 *{ayah.text} ﴿{ayah.ayah_number}﴾*\n\n"
                    )
                    if ayah.translation:
                        message += f"📝 {ayah.translation} ({ayah.ayah_number})\n\n"
                    message += f"📱 {settings.BOT_USERNAME}"

                # Send to user
                await context.bot.send_message(
                    chat_id=user.chat_id,
                    text=message,
                )

                # Mark as sent
                await chat_repo.mark_daily_ayah_sent(user.chat_id)

                logger.info(
                    "Sent daily ayah: telegram_id=%s, surah=%d, ayah=%d",
                    user.chat_id,
                    ayah.surah_number,
                    ayah.ayah_number,
                )

            except Exception as exc:
                logger.exception(
                    "Failed to send daily ayah: telegram_id=%s, error=%s",
                    user.chat_id,
                    exc,
                )
                continue

    except Exception as exc:
        logger.exception("Daily ayah job failed: error=%s", exc)


def schedule_daily_ayah(application: Application) -> None:
    """
    Schedule daily ayah job.

    Runs every minute to check if it's time to send ayah to users.
    """
    job_queue: JobQueue = application.job_queue

    job_queue.run_repeating(
        send_daily_ayah_job,
        interval=60,  # Check every minute
        first=0,  # Start immediately
        name="daily_ayah",
    )

    logger.info("Daily ayah job scheduled (runs every minute)")
