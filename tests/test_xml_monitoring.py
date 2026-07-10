"""Тесты XML-парсера и экстрактора."""

from pathlib import Path

import pytest

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from app.domain.enums import FeedType
from app.infrastructure.xml.extractors import FeedExtractor, resolve_store_feed_date
from app.infrastructure.xml.parser import XmlParser

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def product_xml() -> bytes:
    return (FIXTURES / "product_feed.xml").read_bytes()


@pytest.fixture
def store_xml() -> bytes:
    return (FIXTURES / "store_feed.xml").read_bytes()


def test_parse_product_feed(product_xml: bytes) -> None:
    parser = XmlParser()
    parsed = parser.parse(product_xml, FeedType.PRODUCT.value)
    parser.validate_structure(parsed, FeedType.PRODUCT.value)
    assert parsed.feed_date is not None
    assert parsed.raw_date == "2026-07-10 10:43"
    assert parsed.feed_date.astimezone(MOSCOW_TZ).strftime("%Y-%m-%d %H:%M") == "2026-07-10 10:43"


def test_resolve_store_feed_date(store_xml: bytes) -> None:
    parser = XmlParser()
    parsed = parser.parse(store_xml, FeedType.STORE.value)
    stores = FeedExtractor().extract_stores(parsed.root)
    feed_date = resolve_store_feed_date(stores)
    assert feed_date is not None
    assert feed_date.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y") == "10.07.2026"


def test_extract_categories(product_xml: bytes) -> None:
    parser = XmlParser()
    parsed = parser.parse(product_xml, FeedType.PRODUCT.value)
    categories = FeedExtractor().extract_categories(parsed.root)
    assert len(categories) == 3
    assert categories[1].category_id == "5"
    assert categories[1].parent_id == "1"
    assert categories[1].name == "Кольца"


def test_extract_products(product_xml: bytes) -> None:
    parser = XmlParser()
    parsed = parser.parse(product_xml, FeedType.PRODUCT.value)
    products = FeedExtractor().extract_products(parsed.root)
    assert len(products) == 2
    assert products[0].offer_id == "100"
    assert products[0].category_id == "5"
    assert products[0].pictures == ["https://cdn.example/product.jpg"]
    assert products[0].price_source == "1000"
    assert products[0].oldprice_source is None


def test_extract_stores(store_xml: bytes) -> None:
    parser = XmlParser()
    parsed = parser.parse(store_xml, FeedType.STORE.value)
    stores = FeedExtractor().extract_stores(parsed.root)
    assert len(stores) == 1
    assert stores[0].company_id == "store-1"
    assert stores[0].photos == ["https://cdn.example/store.jpg"]
