"""Telegram-бот с учётом исходящих сообщений."""

from __future__ import annotations

from typing import Any

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.methods import SendMessage, TelegramMethod
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.keyboards.builders import main_menu_keyboard
from app.core.config import Settings
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.services.bot_message_tracker import BotMessageTracker


class TrackingBot(Bot):
    """Бот, который сохраняет ID всех исходящих сообщений пользователям."""

    def __init__(
        self,
        *,
        settings: Settings,
        tracker: BotMessageTracker,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        super().__init__(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self._settings = settings
        self.tracker = tracker
        self._session_factory = session_factory

    async def __call__(self, method: TelegramMethod[Any], request_timeout: int | None = None) -> Any:
        if isinstance(method, SendMessage):
            method = await self._attach_main_menu_if_needed(method)
        result = await super().__call__(method, request_timeout=request_timeout)
        if isinstance(result, Message):
            await self.tracker.track_message(result)
        return result

    async def _attach_main_menu_if_needed(self, method: SendMessage) -> SendMessage:
        if method.reply_markup is not None or self._session_factory is None:
            return method

        chat_id = method.chat_id
        if not isinstance(chat_id, int) or chat_id <= 0:
            return method

        is_admin = await self._is_authorized_chat(chat_id)
        if is_admin is None:
            return method

        return method.model_copy(
            update={"reply_markup": main_menu_keyboard(is_admin=is_admin)},
        )

    async def _is_authorized_chat(self, chat_id: int) -> bool | None:
        async with UnitOfWork(self._session_factory) as uow:
            user = await uow.users.get_by_telegram_id(chat_id)
            if user is None or not user.is_active:
                return None
        return chat_id == self._settings.admin_id
