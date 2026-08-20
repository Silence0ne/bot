from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.database.models.sent_history import SentHistory


class Chat(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chats"

    # Telegram identifiers
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    chat_type: Mapped[str] = mapped_column(String(32))

    # Preferences
    language: Mapped[str] = mapped_column(String(10), default="fa")
    content_mode: Mapped[str] = mapped_column(String(32), default="random_ayah")

    # Daily ayah settings
    # daily_time is user's preferred local time (e.g., "03:15" for 3:15 AM)
    # timezone is user's timezone (e.g., "Asia/Riyadh")
    # The daily ayah job runs in UTC and converts to user's timezone to check if it's their preferred time
    daily_ayah: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_time: Mapped[str] = mapped_column(
        String(5), default="03:15"
    )  # User's local time
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Admin status
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Delivery tracking
    last_daily_sent_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    sent_history: Mapped["SentHistory | None"] = relationship(
        "SentHistory",
        back_populates="chat",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def daily_ayah_hour(self) -> int:
        hour, _minute = self.daily_time.split(":", 1)
        return int(hour)

    @property
    def daily_ayah_minute(self) -> int:
        _hour, minute = self.daily_time.split(":", 1)
        return int(minute)
