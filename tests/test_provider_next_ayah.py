import asyncio
from typing import Any

from app.api.client import APIClient
from app.api.provider import NatiqProvider
from app.cache.quran import QuranCache


def make_client_stub() -> APIClient:
    return object.__new__(APIClient)


def make_provider(
    *,
    ayahs: list[dict[str, Any]],
    takhtits: list[dict[str, Any]],
    surahs: list[dict[str, Any]],
) -> NatiqProvider:
    cache = QuranCache()
    cache.set_ayahs(ayahs)
    cache.set_takhtits(takhtits)
    cache.set_translations([])
    cache.set_surahs(surahs)
    return NatiqProvider(
        client=make_client_stub(),
        cache=cache,
    )


def test_next_ayah_returns_following_ayah_from_same_surah() -> None:
    provider = make_provider(
        ayahs=[
            {"uuid": "1", "text": "first", "number": 1},
            {"uuid": "2", "text": "second", "number": 2},
            {"uuid": "3", "text": "third", "number": 3},
        ],
        takhtits=[
            {"uuid": "1", "surah": 4, "ayah": 14, "surah_uuid": "surah-4"},
            {"uuid": "2", "surah": 4, "ayah": 15, "surah_uuid": "surah-4"},
            {"uuid": "3", "surah": 5, "ayah": 1, "surah_uuid": "surah-5"},
        ],
        surahs=[
            {
                "uuid": "surah-4",
                "number": 4,
                "name": "النساء",
                "location": "madani",
            },
            {
                "uuid": "surah-5",
                "number": 5,
                "name": "المائدة",
                "location": "madani",
            },
        ],
    )

    ayah = asyncio.run(provider.next_ayah("1"))

    assert ayah.text == "second"
    assert ayah.ayah_number == 15
    assert ayah.uuid == "2"
    assert ayah.surah_uuid == "surah-4"
    assert ayah.surah_name == "النساء"
    assert ayah.surah_period == "madani"
    assert ayah.surah_icon == "🕌"


def test_get_ayahs_by_first_ayah_uuid_returns_same_page() -> None:
    provider = make_provider(
        ayahs=[
            {"uuid": "1", "text": "first", "number": 1},
            {"uuid": "2", "text": "second", "number": 2},
            {"uuid": "3", "text": "third", "number": 3},
        ],
        takhtits=[
            {"uuid": "1", "surah": 4, "ayah": 14, "surah_uuid": "surah-4", "page": 77},
            {"uuid": "2", "surah": 4, "ayah": 15, "surah_uuid": "surah-4", "page": 77},
            {"uuid": "3", "surah": 5, "ayah": 1, "surah_uuid": "surah-5", "page": 78},
        ],
        surahs=[
            {
                "uuid": "surah-4",
                "number": 4,
                "name": "النساء",
                "location": "madani",
            },
            {
                "uuid": "surah-5",
                "number": 5,
                "name": "المائدة",
                "location": "madani",
            },
        ],
    )

    page_ayahs = asyncio.run(provider.get_ayahs_by_first_ayah_uuid("1"))

    assert [ayah.uuid for ayah in page_ayahs] == ["1", "2"]
    assert all(ayah.page == 77 for ayah in page_ayahs)


def test_get_ayahs_by_first_ayah_uuid_returns_empty_for_unknown_uuid() -> None:
    provider = make_provider(
        ayahs=[{"uuid": "1", "text": "first", "number": 1}],
        takhtits=[
            {"uuid": "1", "surah": 4, "ayah": 14, "surah_uuid": "surah-4", "page": 77}
        ],
        surahs=[
            {
                "uuid": "surah-4",
                "number": 4,
                "name": "النساء",
                "location": "madani",
            },
        ],
    )

    page_ayahs = asyncio.run(provider.get_ayahs_by_first_ayah_uuid("missing"))

    assert page_ayahs == []


def test_provider_strips_bismillah_when_it_is_the_first_ayah() -> None:
    bismillah_text = "fixture bismillah"
    remaining_text = "fixture first ayah body"
    provider = make_provider(
        ayahs=[
            {
                "uuid": "1",
                "text": f"{bismillah_text} {remaining_text}",
                "number": 1,
            }
        ],
        takhtits=[{"uuid": "1", "surah": 1, "ayah": 1, "surah_uuid": "surah-1"}],
        surahs=[
            {
                "uuid": "surah-1",
                "number": 1,
                "name": "الفاتحة",
                "location": "makki",
                "bismillah": {"is_ayah": True, "text": bismillah_text},
            }
        ],
    )

    ayah = asyncio.run(provider.random_ayah())

    assert ayah.ayah_number == 1
    assert ayah.bismillah_is_ayah is True
    assert ayah.show_bismillah_line is False
    assert ayah.text == remaining_text


def test_provider_shows_bismillah_line_for_first_ayah_when_not_counted_as_ayah() -> (
    None
):
    bismillah_text = "fixture bismillah"
    ayah_text = "fixture first ayah body"
    provider = make_provider(
        ayahs=[{"uuid": "1", "text": ayah_text, "number": 1}],
        takhtits=[{"uuid": "1", "surah": 55, "ayah": 1, "surah_uuid": "surah-55"}],
        surahs=[
            {
                "uuid": "surah-55",
                "number": 55,
                "name": "الرحمن",
                "location": "madani",
                "bismillah": {"is_ayah": False, "text": bismillah_text},
            }
        ],
    )

    ayah = asyncio.run(provider.random_ayah())

    assert ayah.ayah_number == 1
    assert ayah.bismillah_is_ayah is False
    assert ayah.show_bismillah_line is True
    assert ayah.bismillah_text == bismillah_text
    assert ayah.text == ayah_text


def test_provider_does_not_show_bismillah_line_when_surah_has_no_bismillah() -> None:
    provider = make_provider(
        ayahs=[{"uuid": "1", "text": "fixture first ayah body", "number": 1}],
        takhtits=[{"uuid": "1", "surah": 9, "ayah": 1, "surah_uuid": "surah-9"}],
        surahs=[
            {
                "uuid": "surah-9",
                "number": 9,
                "name": "التوبة",
                "location": "madani",
                "bismillah": {"is_ayah": False, "text": ""},
            }
        ],
    )

    ayah = asyncio.run(provider.random_ayah())

    assert ayah.ayah_number == 1
    assert ayah.bismillah_text is None
    assert ayah.show_bismillah_line is False
    assert ayah.text == "fixture first ayah body"
