from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.database.models.user_chat import UserChat


class Chat(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    __tablename__ = "chats"

    user_chats: Mapped[list["UserChat"]] = relationship(
        "UserChat",
        back_populates="chat",
        cascade="all, delete-orphan",
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chat_type: Mapped[str] = mapped_column(String(32))
    daily_ayah: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_time: Mapped[str] = mapped_column(String(5), default="15:15")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Riyad")
