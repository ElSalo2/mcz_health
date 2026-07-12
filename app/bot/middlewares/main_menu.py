"""Middleware восстановления главного меню после inline-действий."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from app.bot.access_flow import restore_main_menu_silent
from app.services.user_service import UserService


class MainMenuCallbackMiddleware(BaseMiddleware):
    """Возвращает reply-меню после callback, когда Telegram его скрывает."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        result = await handler(event, data)

        if not isinstance(event, CallbackQuery) or event.from_user is None:
            return result

        user_service: UserService | None = data.get("user_service")
        bot = data.get("bot")
        if user_service is None or bot is None:
            return result

        telegram_id = event.from_user.id
        if not await user_service.is_authorized(telegram_id):
            return result

        is_admin = await user_service.is_admin(telegram_id)
        await restore_main_menu_silent(bot, telegram_id, is_admin=is_admin)
        return result
