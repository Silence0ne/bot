from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.database.models.sent_history import SentHistory


class Chat(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chats"

    # Telegram Identifiers
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    chat_type: Mapped[str] = mapped_column(String(32))

    # Chat / User Info
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Preferences
    language: Mapped[str] = mapped_column(String(10), default="fa")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Daily Ayah Settings
    daily_ayah: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_time: Mapped[str] = mapped_column(String(5), default="15:15")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Riyad")

    # Relationships
    sent_history: Mapped["SentHistory | None"] = relationship(
        "SentHistory",
        back_populates="chat",
        uselist=False,
        cascade="all, delete-orphan",
    )
