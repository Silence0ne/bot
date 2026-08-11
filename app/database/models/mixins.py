from __future__ import annotations

import uuid
from datetime import datetime
from datetime import timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.database.types import UUIDType


class UUIDMixin:
    uuid: Mapped[uuid.UUID] = mapped_column(
        UUIDType(),
        default=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
