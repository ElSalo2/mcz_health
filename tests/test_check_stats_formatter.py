"""Тесты детальной статистики проверок."""

from datetime import UTC, datetime

from app.bot.formatters.check_formatter import format_check_stats_block, format_last_check_report
from app.domain.entities.feed_check import FeedCheck
from app.domain.enums import CheckStatus, FeedType
from app.domain.value_objects.feed_check_view import FeedCheckView
from app.infrastructure.database.utils import dump_json


def _check(
    *,
    feed_type: FeedType,
    status: CheckStatus,
    stats: dict | None = None,
) -> FeedCheck:
    now = datetime(2026, 7, 10, 14, 0, tzinfo=UTC)
    return FeedCheck(
        id=1,
        feed_type=feed_type,
        status=status,
        started_at=now,
        finished_at=now if status != CheckStatus.RUNNING else None,
        duration_seconds=10.0 if status != CheckStatus.RUNNING else None,
        item_count=100,
        sha256="hash",
        content_size=1000,
        feed_date=now,
        critical_count=0,
        warning_count=0,
        triggered_by="test",
        stats_json=dump_json(stats) if stats else None,
    )


def test_format_check_stats_for_running_product() -> None:
    started = datetime(2026, 7, 11, 6, 41, tzinfo=UTC)
    feed_date = datetime(2026, 7, 11, 0, 0, tzinfo=UTC)
    check = _check(
        feed_type=FeedType.PRODUCT,
        status=CheckStatus.RUNNING,
        stats={
            "items_in_feed": 1000,
            "product_pages_planned": 1000,
            "product_pages_checked": 250,
            "product_pages_ok": 240,
            "product_images_planned": 3000,
            "product_images_checked": 500,
            "product_images_ok": 490,
            "http_total_planned": 4000,
            "http_total_checked": 750,
            "http_total_ok": 730,
            "prices_checked": 1000,
            "stocks_checked": 1000,
            "names_checked": 1000,
            "categories_in_feed": 15637,
            "categories_used_by_products": 19,
            "max_duration_seconds": 18000,
        },
    )
    check.started_at = started
    check.feed_date = feed_date
    text = format_check_stats_block(check)
    assert "товаров в фиде: 1000" in text
    assert "категорий в фиде: 15637" in text
    assert "используется товарами: 19" in text
    assert "250 из 1 000" in text
    assert "HTTP 200: 240" in text
    assert "цен товаров: 1000" in text
    assert "фид сформирован: 11.07.2026 03:00" in text
    assert "начало проверки: 11.07.2026 09:41" in text
    assert "плановое окончание: 11.07.2026 14:41" in text


def test_format_last_check_report_shows_previous_while_running() -> None:
    running = _check(feed_type=FeedType.PRODUCT, status=CheckStatus.RUNNING, stats={"items_in_feed": 10})
    previous = _check(
        feed_type=FeedType.PRODUCT,
        status=CheckStatus.SUCCESS,
        stats={"items_in_feed": 10, "product_pages_planned": 10, "product_pages_checked": 10, "product_pages_ok": 10},
    )
    report = format_last_check_report(
        FeedCheckView(current=running, previous=previous),
        FeedCheckView(current=None),
    )
    assert "Проверка ещё выполняется" in report
    assert "Предыдущая проверка" in report
    assert "завершена успешно" in report
