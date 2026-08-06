from __future__ import annotations

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.models.mixins import TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
    )

    username: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    first_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    language_code: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
    )

    is_bot: Mapped[bool] = mapped_column(default=False)

    chats: Mapped[list["UserChat"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    sent_history: Mapped["SentHistory | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
