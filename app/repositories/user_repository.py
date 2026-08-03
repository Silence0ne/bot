from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select

from app.database.session import Database

logger = logging.getLogger(__name__)


class UserRepository:
    """
    Complete user repository with all CRUD operations and daily ayah support.

    Handles:
    - User creation and retrieval
    - Daily ayah scheduling and sending
    - User preferences management
    - Admin checks
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    async def get_or_create(
        self,
        telegram_id: int,
        first_name: str,
        username: str | None = None,
        last_name: str | None = None,
        language: str = "en",
    ) -> User:
        """
        Get existing user or create new one.

        Args:
            telegram_id: Telegram user ID
            first_name: User's first name
            username: Optional username
            last_name: Optional last name
            language: Language code (default: en)

        Returns:
            User object (new or existing)

        Raises:
            Exception: Database error
        """
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()

                if user:
                    logger.debug(
                        "User found: telegram_id=%s",
                        telegram_id,
                    )
                    return user

                # Create new user with default settings
                user = User(
                    telegram_id=telegram_id,
                    first_name=first_name,
                    username=username,
                    last_name=last_name,
                    language=language,
                    notifications_enabled=True,
                    daily_ayah_enabled=True,
                    daily_ayah_hour=3,
                    daily_ayah_minute=15,
                )

                session.add(user)
                await session.commit()
                await session.refresh(user)

                logger.info(
                    "User created: telegram_id=%s, name=%s, daily_time=03:15",
                    telegram_id,
                    first_name,
                )
                return user

        except Exception as exc:
            logger.exception(
                "Failed to get/create user: telegram_id=%s, error=%s",
                telegram_id,
                exc,
            )
            raise

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """
        Get user by Telegram ID.

        Args:
            telegram_id: Telegram user ID

        Returns:
            User object or None if not found
        """
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                return result.scalar_one_or_none()
        except Exception as exc:
            logger.exception(
                "Failed to get user: telegram_id=%s, error=%s",
                telegram_id,
                exc,
            )
            return None

    async def update_daily_ayah_time(
        self,
        telegram_id: int,
        hour: int,
        minute: int = 0,
    ) -> bool:
        """
        Update daily ayah sending time.

        Args:
            telegram_id: Telegram user ID
            hour: Hour (0-23)
            minute: Minute (0-59)

        Returns:
            True if successful, False otherwise
        """
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            logger.warning(
                "Invalid time: hour=%d, minute=%d",
                hour,
                minute,
            )
            return False

        try:
            async with self._database.session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(
                        "User not found: telegram_id=%s",
                        telegram_id,
                    )
                    return False

                user.daily_ayah_hour = hour
                user.daily_ayah_minute = minute
                await session.commit()

                logger.info(
                    "Updated daily ayah time: telegram_id=%s, %02d:%02d",
                    telegram_id,
                    hour,
                    minute,
                )
                return True

        except Exception as exc:
            logger.exception(
                "Failed to update daily ayah time: telegram_id=%s, error=%s",
                telegram_id,
                exc,
            )
            return False

    async def toggle_daily_ayah(
        self,
        telegram_id: int,
        enabled: bool,
    ) -> bool:
        """
        Enable/disable daily ayah sending.

        Args:
            telegram_id: Telegram user ID
            enabled: True to enable, False to disable

        Returns:
            True if successful, False otherwise
        """
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()

                if not user:
                    return False

                user.daily_ayah_enabled = enabled
                await session.commit()

                logger.info(
                    "Toggled daily ayah: telegram_id=%s, enabled=%s",
                    telegram_id,
                    enabled,
                )
                return True

        except Exception as exc:
            logger.exception(
                "Failed to toggle daily ayah: telegram_id=%s, error=%s",
                telegram_id,
                exc,
            )
            return False

    async def mark_daily_ayah_sent(self, telegram_id: int) -> bool:
        """
        Mark daily ayah as sent today.

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if successful, False otherwise
        """
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()

                if not user:
                    return False

                user.last_daily_ayah_sent_at = date.today().isoformat()
                await session.commit()

                logger.debug(
                    "Marked daily ayah sent: telegram_id=%s, date=%s",
                    telegram_id,
                    user.last_daily_ayah_sent_at,
                )
                return True

        except Exception as exc:
            logger.exception(
                "Failed to mark daily ayah sent: telegram_id=%s, error=%s",
                telegram_id,
                exc,
            )
            return False

    async def should_send_daily_ayah(self, telegram_id: int) -> bool:
        """
        Check if user should receive daily ayah today.

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if should send, False otherwise
        """
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()

                if not user or not user.daily_ayah_enabled:
                    return False

                today = date.today().isoformat()
                if user.last_daily_ayah_sent_at == today:
                    return False

                return True

        except Exception as exc:
            logger.exception(
                "Failed to check daily ayah: telegram_id=%s, error=%s",
                telegram_id,
                exc,
            )
            return False

    async def get_users_for_daily_ayah(
        self,
        hour: int,
        minute: int,
    ) -> list[User]:
        """
        Get all users who should receive daily ayah at specific time.

        Args:
            hour: Hour to check (0-23)
            minute: Minute to check (0-59)

        Returns:
            List of User objects scheduled for this time
        """
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    select(User).where(
                        (User.daily_ayah_enabled)
                        & (User.daily_ayah_hour == hour)
                        & (User.daily_ayah_minute == minute)
                    )
                )
                users = result.scalars().all()

                logger.debug(
                    "Found %d users scheduled for %02d:%02d",
                    len(users),
                    hour,
                    minute,
                )
                return users

        except Exception as exc:
            logger.exception(
                "Failed to get users for daily ayah: hour=%d, minute=%d, error=%s",
                hour,
                minute,
                exc,
            )
            return []

    async def update_preferences(
        self,
        telegram_id: int,
        **kwargs,
    ) -> bool:
        """
        Update user preferences.

        Allowed fields:
        - language
        - notifications_enabled
        - translation_uuid
        - recitation_uuid
        - preferred_mushaf_uuid

        Args:
            telegram_id: Telegram user ID
            **kwargs: Fields to update

        Returns:
            True if successful, False otherwise
        """
        allowed_fields = {
            "language",
            "notifications_enabled",
            "translation_uuid",
            "recitation_uuid",
            "preferred_mushaf_uuid",
        }

        try:
            async with self._database.session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()

                if not user:
                    return False

                for key, value in kwargs.items():
                    if key in allowed_fields and value is not None:
                        setattr(user, key, value)

                await session.commit()
                logger.info(
                    "Updated preferences: telegram_id=%s, fields=%s",
                    telegram_id,
                    list(kwargs.keys()),
                )
                return True

        except Exception as exc:
            logger.exception(
                "Failed to update preferences: telegram_id=%s, error=%s",
                telegram_id,
                exc,
            )
            return False

    async def is_admin(self, telegram_id: int) -> bool:
        """
        Check if user is admin.

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if admin, False otherwise
        """
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    select(User.is_admin).where(User.telegram_id == telegram_id)
                )
                is_admin = result.scalar_one_or_none()
                return bool(is_admin)
        except Exception:
            logger.exception(
                "Failed to check admin status: telegram_id=%s",
                telegram_id,
            )
            return False

    async def get_all_users(self) -> list[User]:
        """
        Get all users (admin only).

        Returns:
            List of all User objects
        """
        try:
            async with self._database.session() as session:
                result = await session.execute(select(User))
                return result.scalars().all()
        except Exception as exc:
            logger.exception("Failed to get all users: error=%s", exc)
            return []

    async def delete_user(self, telegram_id: int) -> bool:
        """
        Delete user and all related data (CASCADE).

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if successful, False otherwise
        """
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()

                if not user:
                    return False

                await session.delete(user)
                await session.commit()

                logger.info(
                    "User deleted: telegram_id=%s",
                    telegram_id,
                )
                return True

        except Exception as exc:
            logger.exception(
                "Failed to delete user: telegram_id=%s, error=%s",
                telegram_id,
                exc,
            )
            return False
