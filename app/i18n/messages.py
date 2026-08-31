from __future__ import annotations

import json
from pathlib import Path

from app.core.config import get_settings

SupportedLanguage = str

LANGUAGE_ALIASES: dict[str, SupportedLanguage] = {
    "fa": "fa",
    "fa-ir": "fa",
    "fa-af": "fa",
    "persian": "fa",
    "farsi": "fa",
    "en": "en",
    "en-us": "en",
    "en-gb": "en",
    "english": "en",
    "ar": "ar",
    "ar-sa": "ar",
    "ar-ae": "ar",
    "arabic": "ar",
    "tr": "tr",
    "tr-tr": "tr",
    "turkish": "tr",
    "az": "az",
    "az-az": "az",
    "azerbaijani": "az",
}

# Load translations from JSON files dynamically
MESSAGES: dict[str, dict[SupportedLanguage, str]] = {}

_LOCALES_DIR = Path(__file__).parent / "locales"

if _LOCALES_DIR.is_dir():
    for lang_file in _LOCALES_DIR.glob("*.json"):
        lang_code = lang_file.stem
        with open(lang_file, "r", encoding="utf-8") as f:
            lang_data = json.load(f)

        for key, value in lang_data.items():
            if key not in MESSAGES:
                MESSAGES[key] = {}
            MESSAGES[key][lang_code] = value


def normalize_language_code(value: str | None) -> str:
    if not value:
        return ""

    return value.strip().replace("_", "-").lower()


def _resolve_supported_language(value: str | None) -> SupportedLanguage | None:
    normalized = normalize_language_code(value)

    if not normalized:
        return None

    if normalized in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[normalized]

    primary = normalized.split("-", 1)[0]
    return LANGUAGE_ALIASES.get(primary)


def get_default_language() -> SupportedLanguage:
    settings = get_settings()
    resolved = _resolve_supported_language(settings.BOT_LANGUAGE)
    return resolved or "fa"


def detect_language(telegram_language_code: str | None) -> SupportedLanguage:
    resolved = _resolve_supported_language(telegram_language_code)

    if resolved:
        return resolved

    return get_default_language()


def get_message(
    key: str,
    language: SupportedLanguage | None = None,
) -> str:
    if language is None:
        language = get_default_language()

    translations = MESSAGES.get(key, {})

    value = translations.get(language)
    if value:
        return str(value)

    default = get_default_language()
    if default != language:
        fallback = translations.get(default)
        if fallback:
            return str(fallback)

    return key
