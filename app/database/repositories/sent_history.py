from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select

if TYPE_CHECKING:
    from app.database.models.sent_history import SentHistory
    from app.database.session import Database

logger = logging.getLogger(__name__)


class SentHistoryRepository:
    def __init__(self, database: "Database") -> None:
        self._database = database

    async def count_all_sent(self) -> int:
        from app.database.models.sent_history import SentHistory

        async with self._database.session() as session:
            stmt = select(func.count()).select_from(SentHistory)
            result = await session.execute(stmt)
            return int(result.scalar() or 0)

    async def get_all_history(self) -> list["SentHistory"]:
        from app.database.models.sent_history import SentHistory

        async with self._database.session() as session:
            stmt = select(SentHistory)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def log_sent(
        self,
        *,
        chat_uuid: uuid.UUID,
        ayah_uuid: uuid.UUID,
        reading_mode: str = "ayah",
    ) -> "SentHistory":
        from app.database.models.sent_history import ReadingMode, SentHistory

        mode = ReadingMode(reading_mode)
        history = SentHistory(
            chat_uuid=chat_uuid,
            ayah_uuid=ayah_uuid,
            type=mode,
        )
        async with self._database.session() as session:
            session.add(history)
            await session.commit()
            await session.refresh(history)
            return history
