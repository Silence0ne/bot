from __future__ import annotations

import asyncio
import logging

import httpx
from telegram.error import InvalidToken

from app.api.checker import APIFeatureChecker
from app.bot.application import create_application
from app.bot.jobs.daily_ayah import schedule_daily_ayah
from app.core.config import validate_runtime_settings
from app.core.container import Container
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


async def check_bot_api(
    url: str,
    retries: int = 5,
) -> None:
    timeout = httpx.Timeout(
        10.0,
        connect=5.0,
    )

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        for attempt in range(1, retries + 1):
            try:
                response = await client.get(url)

                logger.info(
                    "Bot API check attempt %s: HTTP %s",
                    attempt,
                    response.status_code,
                )

                if response.status_code < 500:
                    return

            except httpx.HTTPError as exc:
                logger.warning(
                    "Bot API connection failed (%s/%s): %s",
                    attempt,
                    retries,
                    exc,
                )

            await asyncio.sleep(attempt * 2)

    raise RuntimeError("Bot API unavailable after retries")


async def main() -> None:
    configure_logging()

    settings = validate_runtime_settings()

    logger.info("Starting Quran Bot...")
    logger.info(
        "Configured admin user IDs: %s",
        sorted(settings.admin_user_ids),
    )

    container = Container()
    application = None
    polling_started = False

    try:
        await container.startup()

        logger.info("All services initialized.")

        if settings.BOT_API:
            try:
                await check_bot_api(settings.BOT_API)
            except Exception:
                logger.warning(
                    "Bot API preflight check failed; continuing to initialize polling."
                )

        feature_checker = APIFeatureChecker(settings)
        await feature_checker.detect()

        application = create_application(
            container,
            feature_checker,
        )

        logger.info("Initializing Telegram application...")
        try:
            await application.initialize()
        except InvalidToken as e:
            logger.error(
                "Invalid Telegram bot token: %s. Please set a valid BOT_TOKEN in .env.docker",
                str(e),
            )
            raise

        logger.info("Starting Telegram application...")
        await application.start()

        if application.updater is None:
            raise RuntimeError("Updater is not available")

        # Start polling first so bot can handle commands immediately
        await application.updater.start_polling(
            drop_pending_updates=True,
            poll_interval=2.0,
            timeout=30,
            bootstrap_retries=-1,
        )

        polling_started = True

        logger.info("Bot is now polling and ready to handle commands.")

        # Schedule daily ayah job
        logger.info("Scheduling daily ayah job...")
        await schedule_daily_ayah(application)

        # Load cache after bot is polling (in background, bot is already working)
        logger.info("Loading Quran cache in background...")
        asyncio.create_task(container.load_cache())

        while True:
            await asyncio.sleep(3600)

    except KeyboardInterrupt:
        logger.info("Stopping bot...")

    except Exception:
        logger.exception("Fatal application error")

    finally:
        try:
            if application:
                if application.updater and polling_started:
                    await application.updater.stop()

                if application.running:
                    await application.stop()

                await application.shutdown()
        finally:
            await container.shutdown()

        logger.info("Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
