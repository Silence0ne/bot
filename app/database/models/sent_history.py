from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from app.database.models.user import User

from app.database.base import Base
from app.database.models.mixins import (
    TimestampMixin,
    UUIDMixin,
)
from app.database.types import UUIDType


class SentHistory(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    """
    Stores the user's last reading position.
    """

    __tablename__ = "sent_history"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        unique=True,
        index=True,
    )

    surah_uuid: Mapped[uuid.UUID] = mapped_column(
        UUIDType(),
    )

    ayah_uuid: Mapped[uuid.UUID] = mapped_column(
        UUIDType(),
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="sent_history",
    )
