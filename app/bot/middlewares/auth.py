"""Middleware проверки авторизации."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.bot.keyboards.builders import contact_keyboard
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
        if not isinstance(event, Message) or event.from_user is None:
            return await handler(event, data)

        user_service: UserService | None = data.get("user_service")
        if user_service is None:
            logger.error("UserService не найден в контексте обработчика")
            await event.answer(Messages.INTERNAL_ERROR)
            return None

        telegram_id = event.from_user.id
        if await user_service.is_authorized(telegram_id):
            return await handler(event, data)

        logger.info("Отказ в доступе неавторизованному пользователю: telegram_id=%s", telegram_id)
        await event.answer(Messages.AUTH_REQUEST_CONTACT, reply_markup=contact_keyboard())
        return None
