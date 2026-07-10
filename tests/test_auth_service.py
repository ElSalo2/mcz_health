"""Тесты сервиса авторизации."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.config import Settings
from app.domain.entities.user import User
from app.domain.enums import UserStatus
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.services.auth_service import AuthService
from app.services.user_service import UserService


@dataclass
class FakeTelegramUser:
    id: int
    first_name: str | None = "Иван"
    last_name: str | None = "Петров"
    username: str | None = "ivan_test"
    is_bot: bool = False


@dataclass
class FakeContact:
    phone_number: str
    user_id: int
    first_name: str = "Иван"


class MockNotificationService:
    """Заглушка NotificationService для тестов."""

    def __init__(self) -> None:
        self.admin_messages: list[str] = []

    async def notify_admin(self, text: str) -> None:
        self.admin_messages.append(text)


@pytest.fixture
def auth_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
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


@pytest.mark.asyncio
async def test_auth_success(
    session_factory,
    auth_settings: Settings,
    sample_user: User,
) -> None:
    notification = MockNotificationService()
    auth_service = AuthService(session_factory, notification, auth_settings)

    async with UnitOfWork(session_factory) as uow:
        await uow.users.create(sample_user)

    result = await auth_service.authenticate_contact(
        FakeTelegramUser(id=123456789),  # type: ignore[arg-type]
        FakeContact(phone_number="79001234567", user_id=123456789),  # type: ignore[arg-type]
    )

    assert result.success is True
    assert result.user is not None
    assert result.user.telegram_id == 123456789
    assert result.user.username == "ivan_test"
    assert notification.admin_messages == []


@pytest.mark.asyncio
async def test_auth_identity_failed(
    session_factory,
    auth_settings: Settings,
) -> None:
    notification = MockNotificationService()
    auth_service = AuthService(session_factory, notification, auth_settings)

    result = await auth_service.authenticate_contact(
        FakeTelegramUser(id=111),  # type: ignore[arg-type]
        FakeContact(phone_number="79001234567", user_id=222),  # type: ignore[arg-type]
    )

    assert result.success is False
    assert result.identity_failed is True
    assert notification.admin_messages == []


@pytest.mark.asyncio
async def test_auth_access_denied_not_in_whitelist(
    session_factory,
    auth_settings: Settings,
) -> None:
    notification = MockNotificationService()
    auth_service = AuthService(session_factory, notification, auth_settings)

    result = await auth_service.authenticate_contact(
        FakeTelegramUser(id=123456789),  # type: ignore[arg-type]
        FakeContact(phone_number="79009998877", user_id=123456789),  # type: ignore[arg-type]
    )

    assert result.success is False
    assert result.access_denied is True
    assert result.user_blocked is False
    assert len(notification.admin_messages) == 1
    assert "Новый запрос на доступ" in notification.admin_messages[0]
    assert "+79009998877" in notification.admin_messages[0]


@pytest.mark.asyncio
async def test_auth_blocked_user(
    session_factory,
    auth_settings: Settings,
    sample_user: User,
) -> None:
    notification = MockNotificationService()
    auth_service = AuthService(session_factory, notification, auth_settings)
    sample_user.status = UserStatus.BLOCKED

    async with UnitOfWork(session_factory) as uow:
        await uow.users.create(sample_user)

    result = await auth_service.authenticate_contact(
        FakeTelegramUser(id=123456789),  # type: ignore[arg-type]
        FakeContact(phone_number="79001234567", user_id=123456789),  # type: ignore[arg-type]
    )

    assert result.success is False
    assert result.user_blocked is True
    assert notification.admin_messages == []


@pytest.mark.asyncio
async def test_auth_admin_auto_provision(
    session_factory,
    auth_settings: Settings,
) -> None:
    """Администратор из ADMIN_ID проходит без предварительного whitelist."""
    notification = MockNotificationService()
    auth_service = AuthService(session_factory, notification, auth_settings)

    result = await auth_service.authenticate_contact(
        FakeTelegramUser(id=999),  # type: ignore[arg-type]
        FakeContact(phone_number="79111152266", user_id=999),  # type: ignore[arg-type]
    )

    assert result.success is True
    assert result.user is not None
    assert result.user.phone == "+79111152266"
    assert result.user.telegram_id == 999
    assert notification.admin_messages == []


@pytest.mark.asyncio
async def test_user_service_is_authorized(
    session_factory,
    auth_settings: Settings,
    sample_user: User,
) -> None:
    user_service = UserService(session_factory, auth_settings)

    assert await user_service.is_authorized(123456789) is False

    async with UnitOfWork(session_factory) as uow:
        await uow.users.create(sample_user)

    assert await user_service.is_authorized(123456789) is True


@pytest.mark.asyncio
async def test_user_service_is_admin(
    session_factory,
    auth_settings: Settings,
) -> None:
    user_service = UserService(session_factory, auth_settings)
    assert await user_service.is_admin(999) is True
    assert await user_service.is_admin(123) is False
