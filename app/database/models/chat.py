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

    # Chat / user info
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Preferences
    language: Mapped[str] = mapped_column(String(10), default="fa")
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)
    content_mode: Mapped[str] = mapped_column(String(32), default="random_ayah")

    # Daily ayah settings
    daily_ayah: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_time: Mapped[str] = mapped_column(String(5), default="03:15")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Riyadh")

    # Delivery tracking
    last_daily_sent_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_ayahs_sent: Mapped[int] = mapped_column(BigInteger, default=0)
    total_pages_sent: Mapped[int] = mapped_column(BigInteger, default=0)

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

    @property
    def total_sent(self) -> int:
        return self.total_ayahs_sent + self.total_pages_sent
