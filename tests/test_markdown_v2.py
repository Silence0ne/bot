import re

from app.bot.handlers.random import format_ayah
from app.bot.handlers.random_page import format_page
from app.core.markdown import escape_html, format_html

# In HTML mode only &, <, > are special and must be escaped.
SPECIAL = set("&<>")


def unescape(text: str) -> str:
    return text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")


def _plain_text(html: str) -> str:
    """Remove bold tags, leaving only plain (escaped) text."""
    return unescape(re.sub(r"</?b>", "", html))


def assert_valid_html(html: str) -> None:
    # Remove bold tags, then confirm no raw special chars remain (they would
    # need to have been escaped).
    without_tags = re.sub(r"</?b>", "", html)
    raw = re.sub(r"&(amp|lt|gt);", "", without_tags)
    bad = [c for c in raw if c in SPECIAL]
    assert not bad, f"unescaped HTML special chars: {bad}"


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


def test_escape_html():
    escaped = escape_html("Tom & Jerry <note> a > b")
    assert escaped == "Tom &amp; Jerry &lt;note&gt; a &gt; b"


def test_format_html_preserves_bold():
    out = format_html("**Bold** text (paren) 12.5% yes_no.com")
    assert "<b>Bold</b>" in out
    assert_valid_html(out)


def test_format_html_double_asterisk_bold():
    out = format_html("**Bold** and *single* (paren) 12.5% yes_no.com")
    assert "<b>Bold</b>" in out
    assert "<b>single</b>" in out
    assert "*" not in out
    assert_valid_html(out)


def test_format_html_escapes_ampersand_inside_bold():
    out = format_html("**Tom & Jerry**")
    assert "<b>Tom &amp; Jerry</b>" in out
    assert_valid_html(out)


def test_format_ayah_bold_and_valid():
    ayah = build_ayah()
    out = format_ayah(ayah)
    assert "<b>الفاتحة</b>" in out
    assert "<b>sample text ﴿7﴾</b>" in out
    assert "📝 sample translation (7)" in out
    assert_valid_html(out)


def test_format_ayah_escapes_special_text():
    ayah = build_ayah(
        surah_icon="",
        surah_period="unknown",
        text="spec & < > chars",
        translation="T & < > and (x) 1.2",
        bismillah_text="B & < >",
        show_bismillah_line=True,
    )
    out = format_ayah(ayah)
    assert_valid_html(out)
    assert "<b>" in out


def test_format_page_valid():
    p1 = build_ayah(text="t & < > x", ayah_number=1, surah_name="سورة")
    p2 = build_ayah(text="T & < > x", ayah_number=2, surah_name="سورة")
    assert_valid_html(format_page([p1, p2]))
    assert_valid_html(format_page([p1, p2], show_translation=True))
