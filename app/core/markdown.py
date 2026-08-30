from __future__ import annotations

import re

# Characters that must be escaped in Telegram's MarkdownV2 parse mode.
_MARKDOWN_V2_ESCAPE_CHARS = r"_*[]()~`>#+-=|{}.!"

# Matches a *bold* span (no nesting and no newline inside).
_BOLD_RE = re.compile(r"\*([^*\n]+)\*")


def escape_markdown_v2(text: str) -> str:
    """
    Escape a string so it renders literally in Telegram MarkdownV2.

    Every reserved character is prefixed with a backslash. Call this on any
    dynamic/unknown content (Quran text, translations, usernames, URLs, ...)
    before inserting it into a MarkdownV2 message.
    """
    return re.sub(r"([" + re.escape(_MARKDOWN_V2_ESCAPE_CHARS) + r"])", r"\\\1", text)


def format_markdown_v2(text: str) -> str:
    """
    Make a message safe/suitable for Telegram MarkdownV2.

    Intended for message templates that already contain intentional ``*bold*``
    spans (e.g. help text, admin dashboard, timezone prompts). Every reserved
    character outside those bold spans is escaped, and the contents of a bold
    span are escaped too (so stray special chars inside don't break rendering).
    """
    parts: list[str] = []
    last = 0
    for match in _BOLD_RE.finditer(text):
        escaped_prefix = escape_markdown_v2(text[last : match.start()])
        escaped_bold = escape_markdown_v2(match.group(1))
        parts.append(escaped_prefix)
        parts.append(f"*{escaped_bold}*")
        last = match.end()
    parts.append(escape_markdown_v2(text[last:]))
    return "".join(parts)
