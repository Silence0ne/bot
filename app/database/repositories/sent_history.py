from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.database.session import Database

logger = logging.getLogger(__name__)


class SentHistoryRepository:
    def __init__(self, database: "Database") -> None:
        self._database = database

    # Add your upsert/get methods here later
