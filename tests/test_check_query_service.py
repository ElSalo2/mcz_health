"""Тесты сервиса запросов проверок."""

import pytest

from app.core.config import Settings
from app.domain.entities.feed_check import FeedCheck
from app.domain.enums import CheckStatus, FeedType
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.infrastructure.database.utils import utc_now
from app.locales.ru import Messages
from app.services.check_query_service import CheckQueryService


@pytest.fixture
def query_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
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
async def test_get_last_check_report(session_factory, query_settings: Settings) -> None:
    service = CheckQueryService(session_factory)
    assert await service.get_last_check_report() == Messages.NO_DATA

    now = utc_now()
    async with UnitOfWork(session_factory) as uow:
        await uow.checks.create(
            FeedCheck(
                id=None,
                feed_type=FeedType.PRODUCT,
                status=CheckStatus.SUCCESS,
                started_at=now,
                finished_at=now,
                duration_seconds=10.0,
                item_count=42,
                sha256="hash",
                content_size=None,
                feed_date=now,
                critical_count=1,
                warning_count=2,
                triggered_by="test",
            )
        )

    report = await service.get_last_check_report()
    assert "Каталог товаров" in report
    assert "42" in report


@pytest.mark.asyncio
async def test_get_history_report(session_factory, query_settings: Settings) -> None:
    service = CheckQueryService(session_factory)
    now = utc_now()

    async with UnitOfWork(session_factory) as uow:
        for feed_type in (FeedType.PRODUCT, FeedType.STORE):
            await uow.checks.create(
                FeedCheck(
                    id=None,
                    feed_type=feed_type,
                    status=CheckStatus.SUCCESS,
                    started_at=now,
                    finished_at=now,
                    duration_seconds=5.0,
                    item_count=10,
                    sha256="h",
                    content_size=None,
                    feed_date=None,
                    critical_count=0,
                    warning_count=0,
                    triggered_by="test",
                )
            )

    report = await service.get_history_report(limit=10)
    assert "История автоматических проверок" in report
    assert "Каталог товаров" in report
    assert "Каталог магазинов" in report
