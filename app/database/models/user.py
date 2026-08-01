from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base
from app.database.models.mixins import TimestampMixin, UUIDMixin
from app.database.types import UUIDType

if TYPE_CHECKING:
    from app.database.models.favorite import Favorite
    from app.database.models.reading_progress import ReadingProgress
    from app.database.models.user_chat import UserChat


class User(
    Base,
    UUIDMixin,
    TimestampMixin,
):
    """
    User model with complete profile and daily ayah preferences.

    Stores:
    - Basic info: telegram_id, name, username
    - Preferences: language, notification settings, daily ayah time
    - UUIDs: translation, recitation, mushaf preferences
    - Daily schedule: hour (0-23), minute (0-59), default 3:15 AM
    """

    __tablename__ = "users"

    # Primary keys
    id: Mapped[int] = mapped_column(primary_key=True)

    # Telegram info (required for bot)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )

    # User info
    username: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Preferences
    language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False,
    )

    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    # Notification settings
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Daily ayah schedule (default: 3:15 AM)
    daily_ayah_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    daily_ayah_hour: Mapped[int] = mapped_column(
        Integer,
        default=3,  # 3 AM
        nullable=False,
    )

    daily_ayah_minute: Mapped[int] = mapped_column(
        Integer,
        default=15,  # 15 minutes
        nullable=False,
    )

    # Last sent daily ayah timestamp (to prevent duplicates in same day)
    last_daily_ayah_sent_at: Mapped[str | None] = mapped_column(
        String(10),  # YYYY-MM-DD format
        nullable=True,
    )

    # Content preferences (UUIDs from Natiq API)
    translation_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(),
        nullable=True,
    )

    recitation_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(),
        nullable=True,
    )

    preferred_mushaf_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(),
        nullable=True,
    )

    # Relationships
    favorites: Mapped[list["Favorite"]] = relationship(
        "Favorite",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    reading_progress: Mapped[ReadingProgress | None] = relationship(
        "ReadingProgress",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    user_chats: Mapped[list["UserChat"]] = relationship(
        "UserChat",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, telegram_id={self.telegram_id}, "
            f"first_name={self.first_name!r})>"
        )
