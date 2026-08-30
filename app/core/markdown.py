from __future__ import annotations

import re

# Telegram's HTML parse mode is far simpler than MarkdownV2: only `&`, `<`
# and `>` must be escaped (and only those, even inside <b>...</b>).

# Matches a bold span written with **bold** (or *bold*). Content must not
# contain `*` or a newline (no nesting / no newline inside a span).
_BOLD_RE = re.compile(r"\*\*([^*\n]+)\*\*|\*([^*\n]+)\*")


def escape_html(text: str) -> str:
    """Escape a string so it renders literally in Telegram's HTML mode."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def format_html(text: str) -> str:
    """
    Build a Telegram HTML message from a template that uses **bold** (or
    *bold*). Bold spans become <b>...</b>; all other text is HTML-escaped so
    stray &, <, > can't break rendering.
    """
    parts: list[str] = []
    last = 0
    for match in _BOLD_RE.finditer(text):
        bold = match.group(1) if match.group(1) is not None else match.group(2)
        parts.append(escape_html(text[last : match.start()]))
        parts.append(f"<b>{escape_html(bold)}</b>")
        last = match.end()
    parts.append(escape_html(text[last:]))
    return "".join(parts)
