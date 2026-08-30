import re

from app.bot.handlers.random import format_ayah
from app.bot.handlers.random_page import format_page
from app.core.markdown import escape_markdown_v2, format_markdown_v2

SPECIAL = set("_*[]()~`>#+-=|{}.!")


def unescape(text: str) -> str:
    return re.sub(r"\\.", "", text)


def _plain_text(markdown: str) -> str:
    """Remove intentional bold spans, leaving only plain (escaped) text."""
    without_bold = re.sub(r"\*[^*]*\*", "", markdown)
    return unescape(without_bold)


def assert_valid_markdown_v2(markdown: str) -> None:
    plain = _plain_text(markdown)
    bad = [c for c in plain if c in SPECIAL]
    assert not bad, f"unescaped MarkdownV2 special chars: {bad}"


def build_ayah(**overrides):
    defaults = dict(
        uuid="ayah-1",
        text="sample text",
        translation="sample translation",
        surah_uuid="surah-1",
        surah_name="الفاتحة",
        surah_number=1,
        surah_period="makki",
        surah_icon="🕋",
        bismillah_text=None,
        bismillah_is_ayah=False,
        show_bismillah_line=False,
        ayah_number=7,
        page=1,
        juz=1,
    )
    defaults.update(overrides)
    from app.schemas.ayah import Ayah

    return Ayah(**defaults)


def test_escape_markdown_v2():
    escaped = escape_markdown_v2(
        "(GMT+4) 100% 12.5 f_g h-i.j k,l {x} = y + z - n > m # t ! u _ v * w"
    )
    plain = unescape(escaped)
    assert all(c not in SPECIAL for c in plain)


def test_format_markdown_v2_preserves_bold():
    out = format_markdown_v2("*Bold* and (paren) 12.5% yes_no.com")
    assert "*Bold*" in out
    assert_valid_markdown_v2(out)


def test_format_markdown_v2_double_asterisk_bold():
    out = format_markdown_v2("**Bold** and *single* (paren) 12.5% yes_no.com")
    assert "*Bold*" in out
    assert "*single*" in out
    assert "**" not in out
    assert_valid_markdown_v2(out)


def test_format_ayah_bold_and_valid():
    ayah = build_ayah()
    out = format_ayah(ayah)
    assert "*الفاتحة*" in out
    assert "*sample text ﴿7﴾*" in out
    assert_valid_markdown_v2(out)


def test_format_ayah_escapes_special_text():
    ayah = build_ayah(
        surah_icon="",
        surah_period="unknown",
        text="spec _*[] ( ) ~`>#+-=|{}.! chars",
        translation="T _*[] (x) 1.2 a-b c+d {e} f! g~",
        bismillah_text="B _*[] (x) .!",
        show_bismillah_line=True,
    )
    out = format_ayah(ayah)
    assert_valid_markdown_v2(out)
    # bold must still render on the ayah text line
    assert "📖 *" in out


def test_format_page_valid():
    p1 = build_ayah(text="t .! x_", ayah_number=1, surah_name="سورة")
    p2 = build_ayah(text="T .! x_", ayah_number=2, surah_name="سورة")
    assert_valid_markdown_v2(format_page([p1, p2]))
    assert_valid_markdown_v2(format_page([p1, p2], show_translation=True))
