"""Middleware учёта входящих сообщений пользователя."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.services.bot_message_tracker import BotMessageTracker


class ChatMessageMiddleware(BaseMiddleware):
    """Сохраняет ID входящих сообщений для последующей очистки чата."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tracker: BotMessageTracker | None = data.get("bot_message_tracker")
        if isinstance(event, Message) and tracker is not None:
            if event.from_user is not None and not event.from_user.is_bot:
                await tracker.track_message(event)

        return await handler(event, data)
