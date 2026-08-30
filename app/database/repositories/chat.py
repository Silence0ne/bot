from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings, resolve_timezone
from app.core.constants import ChatType, ContentMode

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.database.models.chat import Chat
    from app.database.session import Database


class ChatRepository:
    def __init__(self, database: "Database") -> None:
        self._database = database

    async def get_by_telegram_id(self, telegram_id: int) -> "Chat | None":
        from app.database.models.chat import Chat

        async with self._database.session() as session:
            stmt = select(Chat).where(Chat.chat_id == telegram_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_or_create(
        self,
        *,
        telegram_id: int,
        chat_type: str = ChatType.PRIVATE.value,
        language: str = "fa",
        enable_daily_ayah: bool = True,
    ) -> "Chat":
        from app.database.models.chat import Chat

        settings = get_settings()

        async with self._database.session() as session:
            chat = await self._get_by_telegram_id(session, telegram_id)

            if chat is not None:
                chat.language = language or chat.language
                await session.commit()
                await session.refresh(chat)
                return chat

            chat = Chat(
                chat_id=telegram_id,
                chat_type=chat_type,
                language=language,
                daily_ayah=enable_daily_ayah,
                daily_time=settings.DAILY_AYAH_DEFAULT_TIME,  # Uses env config (03:15 for Riyadh)
                timezone=settings.DAILY_AYAH_DEFAULT_TIMEZONE,  # Uses env config (Asia/Riyadh)
                daily_type="ayah",  # Default to ayah type
                content_mode=ContentMode.RANDOM_AYAH.value,
            )
            session.add(chat)
            await session.commit()
            await session.refresh(chat)
            logger.info("Created chat record: chat_id=%s", telegram_id)
            return chat

    async def upsert_from_update(
        self,
        *,
        telegram_id: int,
        chat_type: str,
        language: str | None = None,
    ) -> "Chat":
        from app.database.models.chat import Chat

        settings = get_settings()

        async with self._database.session() as session:
            chat = await self._get_by_telegram_id(session, telegram_id)

            if chat is None:
                chat = Chat(
                    chat_id=telegram_id,
                    chat_type=chat_type,
                    language=language or "fa",
                    daily_ayah=chat_type == ChatType.PRIVATE.value,
                    daily_time=settings.DAILY_AYAH_DEFAULT_TIME,  # Uses env config (03:15 for Riyadh)
                    timezone=settings.DAILY_AYAH_DEFAULT_TIMEZONE,  # Uses env config (Asia/Riyadh)
                    daily_type="ayah",  # Default to ayah type
                    content_mode=ContentMode.RANDOM_AYAH.value,
                )
                session.add(chat)
            else:
                chat.chat_type = chat_type
                if language is not None:
                    chat.language = language

            await session.commit()
            await session.refresh(chat)
            return chat

    async def update_preferences(
        self,
        telegram_id: int,
        *,
        language: str | None = None,
        daily_ayah: bool | None = None,
        daily_time: str | None = None,
        timezone: str | None = None,
        content_mode: str | None = None,
        daily_type: str | None = None,
    ) -> "Chat | None":
        async with self._database.session() as session:
            chat = await self._get_by_telegram_id(session, telegram_id)
            if chat is None:
                return None

            if language is not None:
                chat.language = language
            if daily_ayah is not None:
                chat.daily_ayah = daily_ayah
            if daily_time is not None:
                chat.daily_time = daily_time
            if timezone is not None:
                chat.timezone = timezone
            if content_mode is not None:
                chat.content_mode = content_mode
            if daily_type is not None:
                chat.daily_type = daily_type

            await session.commit()
            await session.refresh(chat)
            return chat

    async def list_daily_ayah_enabled(self) -> list["Chat"]:
        from app.database.models.chat import Chat

        async with self._database.session() as session:
            stmt = select(Chat).where(Chat.daily_ayah.is_(True))
            result = await session.execute(stmt)
            chats = list(result.scalars().all())

        logger.info("Found %d users with daily_ayah enabled", len(chats))
        return chats

    async def should_send_daily_ayah(self, telegram_id: int) -> bool:
        chat = await self.get_by_telegram_id(telegram_id)
        if chat is None or not chat.daily_ayah:
            return False

        today = self._local_today(chat.timezone)
        return chat.last_daily_sent_date != today

    async def mark_daily_ayah_sent(self, telegram_id: int) -> None:
        async with self._database.session() as session:
            chat = await self._get_by_telegram_id(session, telegram_id)
            if chat is None:
                return

            chat.last_daily_sent_date = self._local_today(chat.timezone)
            await session.commit()
            await session.refresh(chat)

    async def count_by_type(self) -> dict[str, int]:
        from app.database.models.chat import Chat

        async with self._database.session() as session:
            stmt = select(Chat.chat_type, func.count()).group_by(Chat.chat_type)
            result = await session.execute(stmt)
            rows = result.all()

        counts = {"private": 0, "group": 0, "supergroup": 0, "channel": 0}
        for chat_type, count in rows:
            counts[str(chat_type)] = int(count)
        return counts

    async def get_send_totals(self) -> dict[str, int]:
        from app.database.models.sent_history import ReadingMode, SentHistory

        async with self._database.session() as session:
            ayah_total = await session.scalar(
                select(func.count())
                .select_from(SentHistory)
                .where(SentHistory.type == ReadingMode.AYAH)
            )
            page_total = await session.scalar(
                select(func.count())
                .select_from(SentHistory)
                .where(SentHistory.type == ReadingMode.PAGE)
            )

        return {
            "ayahs": int(ayah_total or 0),
            "pages": int(page_total or 0),
        }

    @staticmethod
    async def _get_by_telegram_id(
        session: AsyncSession,
        telegram_id: int,
    ) -> "Chat | None":
        from app.database.models.chat import Chat

        stmt = select(Chat).where(Chat.chat_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _local_today(timezone_name: str | None) -> date:
        tz = resolve_timezone(timezone_name)
        return datetime.now(tz).date()
