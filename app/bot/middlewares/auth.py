"""Middleware проверки авторизации."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User as TelegramUser

from app.bot.access_flow import reply_unauthorized, send_access_restricted
from app.core.config import Settings
from app.locales.ru import Messages
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Блокирует доступ неавторизованных пользователей к защищённым handlers."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = self._extract_user(event)
        if from_user is None:
            return await handler(event, data)

        user_service: UserService | None = data.get("user_service")
        config: Settings | None = data.get("config")
        if user_service is None or config is None:
            logger.error("UserService или Settings не найдены в контексте обработчика")
            if isinstance(event, Message):
                await event.answer(Messages.INTERNAL_ERROR)
            elif isinstance(event, CallbackQuery):
                await event.answer(Messages.INTERNAL_ERROR, show_alert=True)
            return None

        telegram_id = from_user.id
        if await user_service.is_authorized(telegram_id):
            return await handler(event, data)

        blocked, revoked = await self._resolve_access_state(user_service, telegram_id)
        logger.info(
            "Отказ в доступе: telegram_id=%s, blocked=%s, revoked=%s",
            telegram_id,
            blocked,
            revoked,
        )

        if isinstance(event, CallbackQuery):
            await event.answer(Messages.AUTH_SESSION_EXPIRED, show_alert=True)
            bot = data.get("bot")
            if bot is not None:
                await send_access_restricted(
                    bot,
                    telegram_id,
                    config,
                    blocked=blocked,
                    revoked=revoked,
                )
            return None

        if isinstance(event, Message):
            await reply_unauthorized(
                event,
                config,
                blocked=blocked,
                revoked=revoked,
            )
        return None

    @staticmethod
    def _extract_user(event: TelegramObject) -> TelegramUser | None:
        if isinstance(event, (Message, CallbackQuery)):
            return event.from_user
        return None

    @staticmethod
    async def _resolve_access_state(
        user_service: UserService,
        telegram_id: int,
    ) -> tuple[bool, bool]:
        """
        Возвращает (blocked, revoked).

        revoked=True — пользователь удалён, но ранее мог быть в системе.
        """
        user = await user_service.get_by_telegram_id(telegram_id)
        if user is None:
            if await user_service.had_successful_authorization(telegram_id):
                return False, True
            return False, False
        return not user.is_active, False
