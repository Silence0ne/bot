import asyncio

from app.bot.handlers.superadmin import _resolve_is_superadmin


class StubUserRepository:
    def __init__(self, *, db_admin: bool) -> None:
        self._db_admin = db_admin
        self.calls: list[int] = []

    async def is_superadmin(self, telegram_id: int) -> bool:
        self.calls.append(telegram_id)
        return self._db_admin


def test_resolve_is_superadmin_allows_env_configured_admin_without_db_lookup() -> None:
    repository = StubUserRepository(db_admin=False)

    result = asyncio.run(
        _resolve_is_superadmin(
            123,
            configured_admin_ids={123},
            user_repository=repository,
        )
    )

    assert result is True
    assert repository.calls == []


def test_resolve_is_superadmin_falls_back_to_database_flag() -> None:
    repository = StubUserRepository(db_admin=True)

    result = asyncio.run(
        _resolve_is_superadmin(
            456,
            configured_admin_ids=set(),
            user_repository=repository,
        )
    )

    assert result is True
    assert repository.calls == [456]


def test_resolve_is_superadmin_denies_when_neither_source_grants_access() -> None:
    repository = StubUserRepository(db_admin=False)

    result = asyncio.run(
        _resolve_is_superadmin(
            789,
            configured_admin_ids={111},
            user_repository=repository,
        )
    )

    assert result is False
    assert repository.calls == [789]
