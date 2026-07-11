"""Репозиторий ID сообщений чата для последующей очистки."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import BotChatMessageModel


class BotChatMessageRepository:
    """Хранит message_id сообщений в чатах с пользователями."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, chat_id: int, message_id: int) -> None:
        """Сохраняет ID сообщения, если его ещё нет в журнале чата."""
        existing = await self._session.execute(
            select(BotChatMessageModel.id)
            .where(
                BotChatMessageModel.chat_id == chat_id,
                BotChatMessageModel.message_id == message_id,
            )
            .limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            return

        self._session.add(
            BotChatMessageModel(
                chat_id=chat_id,
                message_id=message_id,
            )
        )
        await self._session.flush()

    async def list_message_ids(self, chat_id: int) -> list[int]:
        """Возвращает все сохранённые message_id чата."""
        result = await self._session.execute(
            select(BotChatMessageModel.message_id)
            .where(BotChatMessageModel.chat_id == chat_id)
            .order_by(BotChatMessageModel.id.asc())
        )
        return list(result.scalars().all())

    async def clear_chat(self, chat_id: int) -> None:
        """Удаляет журнал сообщений чата."""
        await self._session.execute(
            delete(BotChatMessageModel).where(BotChatMessageModel.chat_id == chat_id)
        )
        await self._session.flush()
