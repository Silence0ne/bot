from enum import Enum


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
