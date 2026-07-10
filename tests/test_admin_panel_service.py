"""Тесты административной панели."""

import pytest

from app.core.config import Settings
from app.domain.entities.user import User
from app.domain.enums import UserStatus
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.services.admin_panel_service import AdminPanelService
from app.services.user_service import UserService


@pytest.fixture
def admin_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("BOT_TOKEN", "1234567890:ABCDEFghijklmnopQRSTUVwxyz")
    monkeypatch.setenv("ADMIN_ID", "1")
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
async def test_admin_add_and_list_user(session_factory, admin_settings: Settings) -> None:
    user_service = UserService(session_factory, admin_settings)
    admin_service = AdminPanelService(user_service, session_factory)

    user = await admin_service.add_user_by_phone("79001112233")
    assert user.phone == "+79001112233"

    text = await admin_service.format_users_list()
    assert "+79001112233" in text
    assert "активен" in text


@pytest.mark.asyncio
async def test_admin_toggle_block(session_factory, admin_settings: Settings, sample_user: User) -> None:
    user_service = UserService(session_factory, admin_settings)
    admin_service = AdminPanelService(user_service, session_factory)

    async with UnitOfWork(session_factory) as uow:
        created = await uow.users.create(sample_user)

    blocked = await admin_service.toggle_block(created.id)
    assert blocked.status == UserStatus.BLOCKED

    unblocked = await admin_service.toggle_block(created.id)
    assert unblocked.status == UserStatus.ACTIVE
