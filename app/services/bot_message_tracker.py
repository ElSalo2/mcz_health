"""Учёт и очистка сообщений в чатах Telegram."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.infrastructure.database.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)

_DELETE_BATCH_SIZE = 100


class BotMessageTracker:
    """Сохраняет message_id и удаляет историю переписки с ботом."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def track(self, chat_id: int, message_id: int) -> None:
        """Запоминает сообщение чата."""
        async with UnitOfWork(self._session_factory) as uow:
            await uow.bot_chat_messages.add(chat_id, message_id)

    async def track_message(self, message: Message | None) -> None:
        """Запоминает отправленное или входящее сообщение."""
        if message is None:
            return
        await self.track(message.chat.id, message.message_id)

    async def clear_chat(self, bot: Bot, chat_id: int) -> None:
        """Удаляет все известные сообщения чата и очищает журнал."""
        async with UnitOfWork(self._session_factory) as uow:
            message_ids = await uow.bot_chat_messages.list_message_ids(chat_id)
            await uow.bot_chat_messages.clear_chat(chat_id)

        if not message_ids:
            return

        for offset in range(0, len(message_ids), _DELETE_BATCH_SIZE):
            batch = message_ids[offset : offset + _DELETE_BATCH_SIZE]
            try:
                await bot.delete_messages(chat_id, batch)
            except TelegramAPIError:
                for message_id in batch:
                    try:
                        await bot.delete_message(chat_id, message_id)
                    except TelegramAPIError as exc:
                        logger.debug(
                            "Не удалось удалить сообщение %s в чате %s: %s",
                            message_id,
                            chat_id,
                            exc,
                        )
