from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.database.models.chat import Chat
    from app.database.session import Database

logger = logging.getLogger(__name__)


class ChatRepository:
    def __init__(self, database: "Database") -> None:
        self._database = database

    async def get_by_telegram_id(self, telegram_id: int) -> "Chat | None":
        """
        TODO: Implement fetching chat by Telegram ID.

        Example (adjust based on how your Database session works):
        async with self._database.session() as session:
            stmt = select(Chat).where(Chat.chat_id == telegram_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        """
        raise NotImplementedError(
            "ChatRepository.get_by_telegram_id is not implemented yet."
        )
