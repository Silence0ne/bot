from __future__ import annotations

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.models.mixins import TimestampMixin


class UserChat(Base, TimestampMixin):
    __tablename__ = "user_chats"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "chat_id",
            name="uq_user_chat",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    chat_id: Mapped[int] = mapped_column(
        ForeignKey(
            "chats.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    user: Mapped["User"] = relationship(
        back_populates="chats",
    )

    chat: Mapped["Chat"] = relationship(
        back_populates="user_chats",
    )
