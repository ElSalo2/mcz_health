"""Тесты построения статистики проверки."""

from datetime import UTC, datetime

import pytest

from app.core.config import Settings
from app.domain.enums import FeedType
from app.infrastructure.xml.extractors import FeedExtractor, StoreItem
from app.services.monitoring.check_stats_builder import build_initial_stats


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
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


def _store(*, url: str, info_page: str) -> StoreItem:
    return StoreItem(
        company_id="1",
        name="Магазин",
        address="Москва",
        working_time="10:00-22:00",
        country="Россия",
        latitude=55.7,
        longitude=37.6,
        url=url,
        info_page=info_page,
        actualization_date="10.07.2026",
        actualization_datetime=datetime(2026, 7, 10, tzinfo=UTC),
        photos=["https://cdn.example/store.jpg"],
        gallery_url=None,
        social_links=[],
        raw={},
    )


def test_store_pages_planned_counts_unique_page_urls(settings: Settings) -> None:
    stores = [
        _store(url="https://mczgold.ru", info_page="https://mczgold.ru"),
        _store(url="https://mczgold.ru/shop-2", info_page="https://mczgold.ru/shop-2"),
    ]
    stats = build_initial_stats(
        feed_type=FeedType.STORE,
        items=stores,
        parsed=None,
        settings=settings,
        feed_extractor=FeedExtractor(),
        skip_http=False,
    )
    assert stats.store_pages_planned == 2
    assert stats.max_duration_seconds == settings.max_check_duration_seconds
