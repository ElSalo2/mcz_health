"""Тесты форматирования Telegram-алертов."""

import re

from app.core.config import Settings
from app.locales import messages
from app.services.monitoring.alert_context import (
    enrich_alert_context,
    format_alert_template,
    format_duplicate_values,
)
from app.services.notification_service import NotificationService


def test_enrich_product_page_context() -> None:
    context = enrich_alert_context(
        "PRODUCT_PAGE_UNAVAILABLE",
        {
            "id": "123",
            "name": "Кольцо",
            "url": "https://example.com/ring",
            "status": 404,
        },
    )
    assert context["offer_id"] == "123"
    assert context["product_url"] == "https://example.com/ring"
    assert context["status_code"] == "404"
    assert re.fullmatch(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", context["check_datetime"])


def test_enrich_image_context_keeps_product_and_image_urls() -> None:
    context = enrich_alert_context(
        "PRODUCT_IMAGE_UNAVAILABLE",
        {
            "id": "123",
            "name": "Кольцо",
            "url": "https://cdn.example.com/1.jpg",
            "product_url": "https://example.com/ring",
            "status": 500,
            "number": 1,
        },
    )
    assert context["image_url"] == "https://cdn.example.com/1.jpg"
    assert context["product_url"] == "https://example.com/ring"
    assert context["image_number"] == "1"


def test_format_xml_unavailable_template() -> None:
    enriched = enrich_alert_context(
        "XML_UNAVAILABLE",
        {
            "feed_name": "Товары",
            "status": "503",
            "reason": "HTTP 503",
        },
        feed_url="https://example.com/feed.xml",
    )
    text = format_alert_template(messages.XML_UNAVAILABLE, enriched)
    assert "XML_UNAVAILABLE" in text
    assert "https://example.com/feed.xml" in text
    assert "503" in text
    assert "Время проверки:" in text


def test_format_duplicate_values() -> None:
    assert format_duplicate_values({"a": 2, "b": 3}) == "a (×2), b (×3)"


def test_notification_service_format_alert(monkeypatch) -> None:
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
    settings = Settings()
    service = NotificationService(bot=None, settings=settings)  # type: ignore[arg-type]
    text = service.format_alert(
        "ISSUE_RESOLVED",
        {
            "error_code": "PRODUCT_MISSING_PICTURE",
            "object": "Кольцо",
            "description": "Проблема больше не воспроизводится",
            "datetime": "10.07.2026 13:51",
        },
    )
    assert "✅ Проблема устранена" in text
    assert "PRODUCT_MISSING_PICTURE" in text
    assert "Кольцо" in text
