import logging

from telegram.ext import Application, ContextTypes
from telegram.request import HTTPXRequest

from app.api.checker import APIFeatureChecker
from app.bot.router import register_handlers
from app.core.config import get_settings
from app.core.container import Container

logger = logging.getLogger(__name__)


async def _handle_error(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    logger.exception(
        "Telegram update handler failed. update=%s",
        update,
        exc_info=context.error,
    )


def create_application(
    container: Container,
    feature_checker: APIFeatureChecker,
) -> Application:
    settings = get_settings()

    request = HTTPXRequest(
        connection_pool_size=20,
        connect_timeout=15.0,
        read_timeout=45.0,
        write_timeout=15.0,
        pool_timeout=15.0,
        media_write_timeout=30.0,
        http_version="1.1",
    )

    builder = Application.builder().token(settings.BOT_TOKEN).request(request)

    if settings.BOT_API:
        api = settings.BOT_API.rstrip("/")
        builder = builder.base_url(f"{api}/bot").base_file_url(f"{api}/file/bot")

    application = builder.build()

    application.bot_data["container"] = container
    application.bot_data["user_repository"] = container.chat_repository
    application.bot_data["feature_checker"] = feature_checker

    register_handlers(application)
    application.add_error_handler(_handle_error)

    logger.info("Telegram handlers registered.")

    return application
