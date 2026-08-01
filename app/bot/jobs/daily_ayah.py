from __future__ import annotations

import logging
from datetime import datetime

from telegram.ext import Application, JobQueue

logger = logging.getLogger(__name__)


async def send_daily_ayah_job(context) -> None:
    """
    Send daily ayah to users at their scheduled time.

    Runs every minute and checks if any users have a scheduled send time.
    """
    try:
        from app.core.container import Container
        from app.repositories.user_repository import UserRepository

        container: Container = context.application.bot_data.get("container")
        user_repo: UserRepository = context.application.bot_data.get("user_repository")

        if not container or not user_repo:
            logger.warning("Container or user repository not available")
            return

        now = datetime.now()
        hour = now.hour
        minute = now.minute

        logger.debug(
            "Running daily ayah job: %02d:%02d",
            hour,
            minute,
        )

        # Get all users who should receive ayah at this time
        users = await user_repo.get_users_for_daily_ayah(hour, minute)

        if not users:
            logger.debug("No users scheduled for %02d:%02d", hour, minute)
            return

        logger.info(
            "Sending daily ayah to %d users at %02d:%02d", len(users), hour, minute
        )

        for user in users:
            try:
                # Check if already sent today
                should_send = await user_repo.should_send_daily_ayah(user.telegram_id)

                if not should_send:
                    logger.debug(
                        "Already sent today: telegram_id=%s",
                        user.telegram_id,
                    )
                    continue

                # Get random ayah
                ayah = await container.provider.random_ayah()

                # Format message
                message = (
                    f"🌙 آیه روز (Daily Ayah)\n\n"
                    f"﴿ {ayah.text} ﴾\n\n"
                    f"📖 {ayah.surah_name}\n"
                    f"آیه {ayah.ayah_number} | سوره {ayah.surah_number}"
                )

                if ayah.translation:
                    message += f"\n\n📝 ترجمه:\n{ayah.translation}"

                # Send to user
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                )

                # Mark as sent
                await user_repo.mark_daily_ayah_sent(user.telegram_id)

                logger.info(
                    "Sent daily ayah: telegram_id=%s, surah=%d, ayah=%d",
                    user.telegram_id,
                    ayah.surah_number,
                    ayah.ayah_number,
                )

            except Exception as exc:
                logger.exception(
                    "Failed to send daily ayah: telegram_id=%s, error=%s",
                    user.telegram_id,
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
