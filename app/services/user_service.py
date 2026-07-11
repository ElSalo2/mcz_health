"""Сервис управления пользователями."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.error_handler import handle_service_errors
from app.core.exceptions import DatabaseError
from app.domain.entities.user import User
from app.domain.enums import UserStatus
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.infrastructure.database.utils import normalize_phone

logger = logging.getLogger(__name__)


class UserService:
    """Операции над пользователями и проверка доступа."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings

    @handle_service_errors
    async def is_authorized(self, telegram_id: int) -> bool:
        """Проверяет, авторизован ли пользователь."""
        user = await self.get_by_telegram_id(telegram_id)
        return user is not None and user.is_active

    @handle_service_errors
    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Возвращает пользователя по Telegram ID."""
        async with UnitOfWork(self._session_factory) as uow:
            return await uow.users.get_by_telegram_id(telegram_id)

    @handle_service_errors
    async def is_admin(self, telegram_id: int) -> bool:
        """Проверяет, является ли пользователь администратором."""
        return telegram_id == self._settings.admin_id

    @handle_service_errors
    async def had_successful_authorization(self, telegram_id: int) -> bool:
        """Была ли у пользователя успешная авторизация в прошлом."""
        async with UnitOfWork(self._session_factory) as uow:
            return await uow.users.had_successful_authorization(telegram_id)

    @handle_service_errors
    async def list_users(self) -> list[User]:
        """Возвращает список всех пользователей."""
        async with UnitOfWork(self._session_factory) as uow:
            return await uow.users.list_all()

    @handle_service_errors
    async def approve_access_request(
        self,
        *,
        phone: str,
        telegram_id: int,
        first_name: str | None = None,
        last_name: str | None = None,
        username: str | None = None,
    ) -> User:
        """Добавляет пользователя по заявке администратора с привязкой Telegram."""
        normalized_phone = normalize_phone(phone)
        async with UnitOfWork(self._session_factory) as uow:
            existing_by_telegram = await uow.users.get_by_telegram_id(telegram_id)
            if existing_by_telegram is not None and existing_by_telegram.is_active:
                return existing_by_telegram

            existing = await uow.users.get_by_phone(normalized_phone)
            if existing is not None:
                if existing.status == UserStatus.BLOCKED:
                    existing.status = UserStatus.ACTIVE
                existing.telegram_id = telegram_id
                existing.first_name = first_name
                existing.last_name = last_name
                existing.username = username
                updated = await uow.users.update(existing)
                logger.info(
                    "Пользователь одобрен по заявке (обновлён): telegram_id=%s, phone=%s",
                    telegram_id,
                    normalized_phone,
                )
                return updated

            user = User(
                id=None,
                phone=normalized_phone,
                telegram_id=telegram_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                status=UserStatus.ACTIVE,
            )
            created = await uow.users.create(user)
            logger.info(
                "Пользователь одобрен по заявке (создан): telegram_id=%s, phone=%s",
                telegram_id,
                normalized_phone,
            )
            return created

    @handle_service_errors
    async def add_user(self, phone: str) -> User:
        """Добавляет пользователя по номеру телефона."""
        normalized_phone = normalize_phone(phone)
        async with UnitOfWork(self._session_factory) as uow:
            existing = await uow.users.get_by_phone(normalized_phone)
            if existing is not None:
                raise DatabaseError(
                    "Пользователь с таким номером телефона уже существует",
                    details={"phone": normalized_phone},
                )
            user = User(
                id=None,
                phone=normalized_phone,
                telegram_id=0,
                first_name=None,
                last_name=None,
                username=None,
                status=UserStatus.ACTIVE,
            )
            created = await uow.users.create(user)
            logger.info("Добавлен пользователь: phone=%s", normalized_phone)
            return created

    @handle_service_errors
    async def delete_user(self, user_id: int) -> User:
        """Удаляет пользователя и возвращает удалённую запись."""
        async with UnitOfWork(self._session_factory) as uow:
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise DatabaseError("Пользователь не найден", details={"id": user_id})
            await uow.users.delete(user_id)
            logger.info(
                "Удалён пользователь: id=%s, telegram_id=%s, phone=%s",
                user_id,
                user.telegram_id,
                user.phone,
            )
            return user

    @handle_service_errors
    async def block_user(self, user_id: int) -> User:
        """Блокирует пользователя."""
        return await self._set_status(user_id, UserStatus.BLOCKED)

    @handle_service_errors
    async def unblock_user(self, user_id: int) -> User:
        """Разблокирует пользователя."""
        return await self._set_status(user_id, UserStatus.ACTIVE)

    async def _set_status(self, user_id: int, status: UserStatus) -> User:
        async with UnitOfWork(self._session_factory) as uow:
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise DatabaseError("Пользователь не найден", details={"id": user_id})
            user.status = status
            updated = await uow.users.update(user)
            logger.info("Изменён статус пользователя id=%s: %s", user_id, status.value)
            return updated
