from enum import Enum


class Language(str, Enum):
    ENGLISH = "en"
    PERSIAN = "fa"
    ARABIC = "ar"
    TURKISH = "tr"


class ChatType(str, Enum):
    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


class ContentMode(str, Enum):
    RANDOM_AYAH = "random_ayah"
    RANDOM_PAGE = "random_page"
    SPECIFIC_AYAH = "specific_ayah"
    SPECIFIC_PAGE = "specific_page"


class UserState(str, Enum):
    NONE = "none"

    SEARCH = "search"

    SETTINGS = "settings"

    SELECT_TRANSLATION = "select_translation"

    SELECT_RECITER = "select_reciter"

    AWAIT_PAGE_NUMBER = "await_page_number"

    AWAIT_SURAH_NUMBER = "await_surah_number"

    AWAIT_AYAH_NUMBER = "await_ayah_number"


class CachePrefix(str, Enum):
    USER = "user"

    CHAT = "chat"

    AYAH = "ayah"

    SURAH = "surah"

    TRANSLATION = "translation"

    RECITATION = "recitation"

    SETTINGS = "settings"

    STATE = "state"

    DAILY = "daily"
