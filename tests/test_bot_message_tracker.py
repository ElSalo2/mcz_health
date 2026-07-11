"""Тесты учёта и очистки сообщений чата."""

import pytest

from app.infrastructure.database.unit_of_work import UnitOfWork
from app.services.bot_message_tracker import BotMessageTracker


@pytest.mark.asyncio
async def test_bot_message_tracker_stores_and_clears_chat(session_factory) -> None:
    tracker = BotMessageTracker(session_factory)

    await tracker.track(chat_id=1001, message_id=10)
    await tracker.track(chat_id=1001, message_id=11)
    await tracker.track(chat_id=1002, message_id=20)

    async with UnitOfWork(session_factory) as uow:
        chat_one = await uow.bot_chat_messages.list_message_ids(1001)
        chat_two = await uow.bot_chat_messages.list_message_ids(1002)

    assert chat_one == [10, 11]
    assert chat_two == [20]

    class FakeBot:
        def __init__(self) -> None:
            self.deleted_batches: list[list[int]] = []

        async def delete_messages(self, chat_id: int, message_ids: list[int]) -> bool:
            self.deleted_batches.append(message_ids)
            return True

        async def delete_message(self, chat_id: int, message_id: int) -> bool:
            return True

    bot = FakeBot()
    await tracker.clear_chat(bot, 1001)  # type: ignore[arg-type]

    assert bot.deleted_batches == [[10, 11]]

    async with UnitOfWork(session_factory) as uow:
        assert await uow.bot_chat_messages.list_message_ids(1001) == []
        assert await uow.bot_chat_messages.list_message_ids(1002) == [20]
