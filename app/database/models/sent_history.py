from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.models.mixins import TimestampMixin, UUIDMixin
from app.database.types import UUIDType

if TYPE_CHECKING:
    from app.database.models.chat import Chat


class SentHistory(Base, UUIDMixin, TimestampMixin):
    """
    Stores the chat's last reading position (surah and ayah).
    """

    __tablename__ = "sent_history"

    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(),
        ForeignKey(
            "chats.uuid",
            ondelete="CASCADE",
        ),
        unique=True,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(32))
    ayah_uuid: Mapped[uuid.UUID] = mapped_column(UUIDType())

    chat: Mapped["Chat"] = relationship(
        "Chat",
        back_populates="sent_history",
    )
