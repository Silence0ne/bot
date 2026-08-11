from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select

if TYPE_CHECKING:
    from app.database.models.sent_history import SentHistory
    from app.database.session import Database

logger = logging.getLogger(__name__)


class SentHistoryRepository:
    def __init__(self, database: "Database") -> None:
        self._database = database

    async def get_by_chat_uuid(self, chat_uuid: uuid.UUID) -> "SentHistory | None":
        from app.database.models.sent_history import SentHistory

        async with self._database.session() as session:
            stmt = select(SentHistory).where(SentHistory.chat_id == chat_uuid)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def upsert_position(
        self,
        *,
        chat_uuid: uuid.UUID,
        ayah_uuid: uuid.UUID,
        reading_mode: str = "ayah",
    ) -> "SentHistory":
        from app.database.models.sent_history import ReadingMode, SentHistory

        mode = ReadingMode(reading_mode)

        async with self._database.session() as session:
            stmt = select(SentHistory).where(SentHistory.chat_id == chat_uuid)
            result = await session.execute(stmt)
            history = result.scalar_one_or_none()

            if history is None:
                history = SentHistory(
                    chat_id=chat_uuid,
                    ayah_uuid=ayah_uuid,
                    type=mode,
                )
                session.add(history)
            else:
                history.ayah_uuid = ayah_uuid
                history.type = mode

            await session.commit()
            await session.refresh(history)
            return history
