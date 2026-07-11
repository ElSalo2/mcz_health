"""Тесты одобрения и отклонения заявок на доступ."""

from __future__ import annotations

import pytest

from app.bot.keyboards.builders import access_request_keyboard
from app.core.config import Settings
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.services.user_service import UserService


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("BOT_TOKEN", "1234567890:ABCDEFghijklmnopQRSTUVwxyz")
    monkeypatch.setenv("ADMIN_ID", "999")
    monkeypatch.setenv(
        "STORE_FEED_URL",
        "https://st.sunlight.net/media/feed/outlets/yandex_outlets_mcz.xml",
    )
    monkeypatch.setenv(
        "PRODUCT_FEED_URL",
        "https://st.sunlight.net/media/feed/anyquery_mcz.xml",
    )
    return Settings()


def test_access_request_keyboard_callback_data() -> None:
    keyboard = access_request_keyboard(123456789, "+79001234567")
    approve_btn = keyboard.inline_keyboard[0][0]
    reject_btn = keyboard.inline_keyboard[0][1]
    assert approve_btn.callback_data == "access:approve:123456789:79001234567"
    assert reject_btn.callback_data == "access:reject:123456789"
    assert len(approve_btn.callback_data) <= 64


@pytest.mark.asyncio
async def test_approve_access_request_creates_user(
    session_factory,
    settings: Settings,
) -> None:
    user_service = UserService(session_factory, settings)

    user = await user_service.approve_access_request(
        phone="+79005554433",
        telegram_id=555444333,
        first_name="Анна",
        last_name="Смирнова",
        username="anna_test",
    )

    assert user.phone == "+79005554433"
    assert user.telegram_id == 555444333
    assert user.first_name == "Анна"
    assert user.username == "anna_test"
    assert await user_service.is_authorized(555444333) is True


@pytest.mark.asyncio
async def test_approve_access_request_updates_existing_phone_record(
    session_factory,
    settings: Settings,
    sample_user,
) -> None:
    user_service = UserService(session_factory, settings)
    sample_user.telegram_id = 0

    async with UnitOfWork(session_factory) as uow:
        await uow.users.create(sample_user)

    user = await user_service.approve_access_request(
        phone=sample_user.phone,
        telegram_id=777888999,
        first_name="Иван",
        last_name="Петров",
        username="ivan_new",
    )

    assert user.telegram_id == 777888999
    assert user.username == "ivan_new"
    assert await user_service.is_authorized(777888999) is True
