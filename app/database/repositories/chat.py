from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ChatType, ContentMode

if TYPE_CHECKING:
    from app.database.models.chat import Chat
    from app.database.session import Database

logger = logging.getLogger(__name__)


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
        first_name: str | None = None,
        last_name: str | None = None,
        username: str | None = None,
        title: str | None = None,
        language: str = "fa",
        enable_daily_ayah: bool = True,
    ) -> "Chat":
        from app.database.models.chat import Chat

        async with self._database.session() as session:
            chat = await self._get_by_telegram_id(session, telegram_id)

            if chat is not None:
                chat.first_name = first_name or chat.first_name
                chat.last_name = last_name or chat.last_name
                chat.username = username or chat.username
                chat.title = title or chat.title
                chat.language = language or chat.language
                await session.commit()
                await session.refresh(chat)
                return chat

            chat = Chat(
                chat_id=telegram_id,
                chat_type=chat_type,
                first_name=first_name,
                last_name=last_name,
                username=username,
                title=title,
                language=language,
                daily_ayah=enable_daily_ayah,
                daily_time="03:15",
                content_mode=ContentMode.RANDOM_AYAH.value,
            )
            session.add(chat)
            await session.commit()
            await session.refresh(chat)
            logger.info(
                "Created chat record: chat_id=%s type=%s", telegram_id, chat_type
            )
            return chat

    async def upsert_from_update(
        self,
        *,
        telegram_id: int,
        chat_type: str,
        first_name: str | None = None,
        last_name: str | None = None,
        username: str | None = None,
        title: str | None = None,
        language: str | None = None,
    ) -> "Chat":
        from app.database.models.chat import Chat

        async with self._database.session() as session:
            chat = await self._get_by_telegram_id(session, telegram_id)

            if chat is None:
                chat = Chat(
                    chat_id=telegram_id,
                    chat_type=chat_type,
                    first_name=first_name,
                    last_name=last_name,
                    username=username,
                    title=title,
                    language=language or "fa",
                    daily_ayah=chat_type == ChatType.PRIVATE.value,
                    daily_time="03:15",
                    content_mode=ContentMode.RANDOM_AYAH.value,
                )
                session.add(chat)
            else:
                chat.chat_type = chat_type
                if first_name is not None:
                    chat.first_name = first_name
                if last_name is not None:
                    chat.last_name = last_name
                if username is not None:
                    chat.username = username
                if title is not None:
                    chat.title = title
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

            await session.commit()
            await session.refresh(chat)
            return chat

    async def list_due_for_daily_ayah(self) -> list["Chat"]:
        from app.database.models.chat import Chat

        async with self._database.session() as session:
            stmt = select(Chat).where(Chat.daily_ayah.is_(True))
            result = await session.execute(stmt)
            chats = list(result.scalars().all())

        due: list[Chat] = []
        for chat in chats:
            if self._is_due_now(chat):
                due.append(chat)
        return due

    async def should_send_daily_ayah(self, telegram_id: int) -> bool:
        chat = await self.get_by_telegram_id(telegram_id)
        if chat is None or not chat.daily_ayah:
            return False

        today = self._local_today(chat.timezone)
        return chat.last_daily_sent_date != today

    async def mark_daily_sent(
        self,
        telegram_id: int,
        *,
        sent_pages: bool = False,
    ) -> None:
        # Note: 'total_ayahs_sent' and 'total_pages_sent' were removed from Chat model.
        # History is now managed solely via SentHistoryRepository.
        pass

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
    def _local_today(timezone_name: str) -> date:
        try:
            tz = ZoneInfo(timezone_name)
        except Exception:
            tz = ZoneInfo("UTC")
        return datetime.now(tz).date()

    @classmethod
    def _is_due_now(cls, chat: "Chat") -> bool:
        try:
            tz = ZoneInfo(chat.timezone)
        except Exception:
            tz = ZoneInfo("UTC")

        now = datetime.now(tz)
        try:
            hour_str, minute_str = chat.daily_time.split(":", 1)
            due_hour = int(hour_str)
            due_minute = int(minute_str)
        except ValueError:
            logger.warning(
                "Invalid daily_time for chat_id=%s: %s", chat.chat_id, chat.daily_time
            )
            return False

        return now.hour == due_hour and now.minute == due_minute
