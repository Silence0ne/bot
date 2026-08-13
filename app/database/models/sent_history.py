from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.models.mixins import TimestampMixin, UUIDMixin
from app.database.types import UUIDType

if TYPE_CHECKING:
    from app.database.models.chat import Chat


class ReadingMode(str, enum.Enum):
    AYAH = "ayah"
    PAGE = "page"


class SentHistory(Base, UUIDMixin, TimestampMixin):
    """
    Stores the chat's last reading position and tracking mode.
    """

    __tablename__ = "sent_history"

    chat_uuid: Mapped[uuid.UUID] = mapped_column(
        UUIDType(),
        ForeignKey(
            "chats.uuid",
            ondelete="CASCADE",
        ),
        index=True,
    )
    # The unique=True constraint has been removed.

    type: Mapped[ReadingMode] = mapped_column(
        Enum(ReadingMode, native_enum=False, length=5),
        default=ReadingMode.AYAH,
        nullable=False,
    )

    ayah_uuid: Mapped[uuid.UUID] = mapped_column(UUIDType())

    chat: Mapped["Chat"] = relationship(
        "Chat",
        back_populates="sent_history",
    )
