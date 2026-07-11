"""Тесты сбора URL для HTTP-проверки."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.core.config import Settings
from app.infrastructure.xml.extractors import ProductItem, StoreItem
from app.services.monitoring.url_collector import (
    collect_all_http_urls,
    collect_product_http_urls,
    collect_store_http_urls,
    store_page_urls,
)


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


@pytest.fixture
def sample_product() -> ProductItem:
    return ProductItem(
        offer_id="1",
        name="Кольцо",
        name_source="Кольцо",
        vendor="MCZ",
        price="1000",
        price_source="1000",
        oldprice_source=None,
        url="https://mczgold.ru/product/1",
        url_source="https://mczgold.ru/product/1",
        available_source="true",
        stock_source=None,
        pictures=[
            "https://cdn.example/img1.jpg",
            "https://cdn.example/img2.jpg",
        ],
        category_id="5",
        raw={},
    )


@pytest.fixture
def sample_store() -> StoreItem:
    return StoreItem(
        company_id="abc",
        name="Магазин",
        address="Москва",
        working_time="10:00-22:00",
        country="Россия",
        latitude=55.7,
        longitude=37.6,
        url="https://mczgold.ru",
        info_page="https://mczgold.ru/info",
        actualization_date="10.07.2026",
        actualization_datetime=datetime(2026, 7, 10, tzinfo=UTC),
        photos=["https://cdn.example/store1.jpg"],
        gallery_url="https://mczgold.ru",
        social_links=["https://t.me/mczjewelry"],
        raw={},
    )


def test_collect_product_urls_fast_mode(
    settings: Settings,
    sample_product: ProductItem,
) -> None:
    urls = collect_product_http_urls([sample_product], settings)
    assert urls == [
        "https://mczgold.ru/product/1",
        "https://cdn.example/img1.jpg",
        "https://cdn.example/img2.jpg",
    ]


def test_collect_product_urls_without_images(
    settings: Settings,
    sample_product: ProductItem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHECK_PRODUCT_IMAGES", "false")
    no_images_settings = Settings()
    urls = collect_product_http_urls([sample_product], no_images_settings)
    assert urls == ["https://mczgold.ru/product/1"]


def test_collect_product_urls_full_mode(
    settings: Settings,
    sample_product: ProductItem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHECK_MODE", "FULL")
    full_settings = Settings()
    urls = collect_product_http_urls([sample_product], full_settings)
    assert urls == [
        "https://mczgold.ru/product/1",
        "https://cdn.example/img1.jpg",
        "https://cdn.example/img2.jpg",
    ]


def test_store_page_urls_deduplicates_same_url(sample_store: StoreItem) -> None:
    store = replace(
        sample_store,
        url="https://mczgold.ru",
        info_page="https://mczgold.ru",
    )
    assert store_page_urls(store) == ["https://mczgold.ru"]


def test_collect_store_urls_deduplicates_same_page_urls(
    settings: Settings,
    sample_store: StoreItem,
) -> None:
    store = replace(
        sample_store,
        url="https://mczgold.ru",
        info_page="https://mczgold.ru",
    )
    urls = collect_store_http_urls([store], settings)
    assert urls == [
        "https://mczgold.ru",
        "https://cdn.example/store1.jpg",
    ]


def test_collect_store_urls_with_photos(
    settings: Settings,
    sample_store: StoreItem,
) -> None:
    urls = collect_store_http_urls([sample_store], settings)
    assert urls == [
        "https://mczgold.ru",
        "https://mczgold.ru/info",
        "https://cdn.example/store1.jpg",
    ]


def test_collect_store_social_links_when_enabled(
    settings: Settings,
    sample_store: StoreItem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHECK_SOCIAL_LINKS", "true")
    social_settings = Settings()
    urls = collect_store_http_urls([sample_store], social_settings)
    assert "https://t.me/mczjewelry" in urls


def test_collect_all_deduplicates_across_feeds(
    settings: Settings,
    sample_product: ProductItem,
    sample_store: StoreItem,
) -> None:
    shared_store = StoreItem(
        company_id="abc2",
        name="Магазин 2",
        address="Москва",
        working_time="10:00-22:00",
        country="Россия",
        latitude=55.7,
        longitude=37.6,
        url="https://mczgold.ru/product/1",
        info_page="https://mczgold.ru/info",
        actualization_date="10.07.2026",
        actualization_datetime=datetime(2026, 7, 10, tzinfo=UTC),
        photos=[],
        gallery_url=None,
        social_links=[],
        raw={},
    )
    urls = collect_all_http_urls([sample_product], [sample_store, shared_store], settings)
    assert urls.count("https://mczgold.ru/product/1") == 1
