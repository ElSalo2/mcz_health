"""Сервис авторизации пользователей."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from aiogram.types import Contact, User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.error_handler import handle_service_errors
from app.domain.entities.user import User
from app.domain.enums import UserStatus
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.infrastructure.database.utils import normalize_phone
from app.bot.keyboards.builders import access_request_keyboard
from app.locales.ru import Messages
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AuthResult:
    """Результат попытки авторизации."""

    success: bool
    user: User | None = None
    reason: str | None = None
    access_denied: bool = False
    identity_failed: bool = False
    user_blocked: bool = False


class AuthService:
    """Авторизация через подтверждение номера телефона в Telegram."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        notification_service: NotificationService,
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._notification_service = notification_service
        self._settings = settings

    @handle_service_errors
    async def authenticate_contact(
        self,
        telegram_user: TelegramUser,
        contact: Contact,
    ) -> AuthResult:
        """Проверяет контакт пользователя и выполняет авторизацию."""
        phone = contact.phone_number or ""

        if contact.user_id != telegram_user.id:
            logger.warning(
                "Попытка авторизации чужим контактом: telegram_id=%s, contact_user_id=%s",
                telegram_user.id,
                contact.user_id,
            )
            await self._log_attempt(telegram_user.id, phone, success=False, reason="identity_mismatch")
            return AuthResult(success=False, identity_failed=True, reason="identity_mismatch")

        try:
            normalized_phone = normalize_phone(phone)
        except ValueError:
            await self._log_attempt(telegram_user.id, phone, success=False, reason="invalid_phone")
            return AuthResult(success=False, identity_failed=True, reason="invalid_phone")

        async with UnitOfWork(self._session_factory) as uow:
            if telegram_user.id == self._settings.admin_id:
                return await self._authenticate_admin(uow, telegram_user, normalized_phone)

            user = await uow.users.get_by_phone(normalized_phone)

            if user is None:
                logger.info(
                    "Запрос доступа от неавторизованного номера: telegram_id=%s, phone=%s",
                    telegram_user.id,
                    normalized_phone,
                )
                await uow.users.log_authorization(
                    telegram_id=telegram_user.id,
                    phone=normalized_phone,
                    success=False,
                    reason="not_in_whitelist",
                )
                await self._notify_admin_access_request(telegram_user, normalized_phone)
                return AuthResult(success=False, access_denied=True, reason="not_in_whitelist")

            if user.status == UserStatus.BLOCKED:
                logger.info(
                    "Попытка входа заблокированного пользователя: telegram_id=%s, phone=%s",
                    telegram_user.id,
                    normalized_phone,
                )
                await uow.users.log_authorization(
                    telegram_id=telegram_user.id,
                    phone=normalized_phone,
                    success=False,
                    reason="user_blocked",
                )
                return AuthResult(success=False, access_denied=True, user_blocked=True, reason="user_blocked")

            user.telegram_id = telegram_user.id
            user.first_name = telegram_user.first_name
            user.last_name = telegram_user.last_name
            user.username = telegram_user.username
            updated_user = await uow.users.update(user)

            await uow.users.log_authorization(
                telegram_id=telegram_user.id,
                phone=normalized_phone,
                success=True,
                reason=None,
            )

        logger.info("Успешная авторизация: telegram_id=%s, phone=%s", telegram_user.id, normalized_phone)
        return AuthResult(success=True, user=updated_user)

    async def _authenticate_admin(
        self,
        uow: UnitOfWork,
        telegram_user: TelegramUser,
        normalized_phone: str,
    ) -> AuthResult:
        """Автоматически авторизует администратора без предварительного whitelist."""
        user = await uow.users.get_by_phone(normalized_phone)

        if user is None:
            user = User(
                id=None,
                phone=normalized_phone,
                telegram_id=telegram_user.id,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                username=telegram_user.username,
                status=UserStatus.ACTIVE,
            )
            user = await uow.users.create(user)
            logger.info(
                "Администратор автоматически добавлен в whitelist: telegram_id=%s, phone=%s",
                telegram_user.id,
                normalized_phone,
            )
        else:
            if user.status == UserStatus.BLOCKED:
                user.status = UserStatus.ACTIVE
            user.telegram_id = telegram_user.id
            user.first_name = telegram_user.first_name
            user.last_name = telegram_user.last_name
            user.username = telegram_user.username
            user = await uow.users.update(user)

        await uow.users.log_authorization(
            telegram_id=telegram_user.id,
            phone=normalized_phone,
            success=True,
            reason="admin_auto",
        )
        logger.info(
            "Успешная авторизация администратора: telegram_id=%s, phone=%s",
            telegram_user.id,
            normalized_phone,
        )
        return AuthResult(success=True, user=user)

    async def _log_attempt(
        self,
        telegram_id: int,
        phone: str,
        *,
        success: bool,
        reason: str | None,
    ) -> None:
        async with UnitOfWork(self._session_factory) as uow:
            await uow.users.log_authorization(
                telegram_id=telegram_id,
                phone=phone,
                success=success,
                reason=reason,
            )

    async def _notify_admin_access_request(self, telegram_user: TelegramUser, phone: str) -> None:
        username = (
            f"@{telegram_user.username}"
            if telegram_user.username
            else "не указан"
        )
        text = Messages.ACCESS_REQUEST_ADMIN.format(
            first_name=telegram_user.first_name or "—",
            last_name=telegram_user.last_name or "—",
            username=username,
            telegram_id=telegram_user.id,
        )
        keyboard = access_request_keyboard(telegram_user.id, phone)
        await self._notification_service.notify_admin(text, reply_markup=keyboard)
