"""Telegram-бот с учётом исходящих сообщений."""

from __future__ import annotations

from typing import Any

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.methods import TelegramMethod
from aiogram.types import Message

from app.core.config import Settings
from app.services.bot_message_tracker import BotMessageTracker


class TrackingBot(Bot):
    """Бот, который сохраняет ID всех исходящих сообщений пользователям."""

    def __init__(
        self,
        *,
        settings: Settings,
        tracker: BotMessageTracker,
    ) -> None:
        super().__init__(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.tracker = tracker

    async def __call__(self, method: TelegramMethod[Any], request_timeout: int | None = None) -> Any:
        result = await super().__call__(method, request_timeout=request_timeout)
        if isinstance(result, Message):
            await self.tracker.track_message(result)
        return result
