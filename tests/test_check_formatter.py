"""Тесты форматирования проверок."""

from datetime import UTC, datetime

from app.bot.formatters.check_formatter import (
    format_check_cycle_completed,
    format_datetime_moscow,
    format_duration,
    format_feed_check_summary,
    format_feed_date,
    format_history_report,
    format_last_check_report,
)
from app.domain.entities.feed_check import FeedCheck
from app.domain.enums import CheckStatus, FeedType
from app.locales.ru import Messages


def _sample_check(feed_type: FeedType, item_count: int = 100) -> FeedCheck:
    now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    return FeedCheck(
        id=1,
        feed_type=feed_type,
        status=CheckStatus.SUCCESS,
        started_at=now,
        finished_at=now,
        duration_seconds=125.0,
        item_count=item_count,
        sha256="abc",
        content_size=None,
        feed_date=now,
        critical_count=2,
        warning_count=5,
        triggered_by="manual",
    )


def test_format_datetime_moscow_from_naive_utc() -> None:
    """SQLite возвращает UTC без tzinfo — показываем московское время."""
    assert format_datetime_moscow(datetime(2026, 7, 10, 9, 58, 33)) == "10.07.2026 12:58"


def test_format_duration() -> None:
    assert format_duration(125.0) == "2 мин 5 сек"
    assert format_duration(30.0) == "30 сек"
    assert format_duration(None) == Messages.DURATION_UNKNOWN
    assert format_duration(7200.0) == "2 ч 0 мин"


def test_format_last_check_report_empty() -> None:
    assert format_last_check_report(None, None) == Messages.NO_DATA


def test_format_feed_date_unknown() -> None:
    assert format_feed_date(None) == Messages.FEED_DATE_UNKNOWN


def test_format_last_check_report_store_first() -> None:
    report = format_last_check_report(
        _sample_check(FeedType.PRODUCT, 100),
        _sample_check(FeedType.STORE, 17),
    )
    store_pos = report.find("Каталог магазинов")
    product_pos = report.find("Каталог товаров")
    assert store_pos != -1
    assert product_pos != -1
    assert store_pos < product_pos


def test_format_last_check_report_with_data() -> None:
    report = format_last_check_report(_sample_check(FeedType.PRODUCT), None)
    assert "Последняя автоматическая проверка" in report
    assert "Каталог товаров" in report
    assert "100" in report


def test_format_history_report() -> None:
    checks = [
        _sample_check(FeedType.PRODUCT, 100),
        _sample_check(FeedType.STORE, 15),
    ]
    report = format_history_report(checks)
    assert "История автоматических проверок" in report
    assert "1." in report
    assert "2." in report


def test_format_history_report_running() -> None:
    now = datetime(2026, 7, 10, 12, 15, tzinfo=UTC)
    running = FeedCheck(
        id=1,
        feed_type=FeedType.PRODUCT,
        status=CheckStatus.RUNNING,
        started_at=now,
        finished_at=None,
        duration_seconds=None,
        item_count=None,
        sha256=None,
        content_size=None,
        feed_date=None,
        critical_count=0,
        warning_count=0,
        triggered_by="background",
    )
    report = format_history_report([running])
    assert "Сейчас выполняется" in report
    assert "Крит.:" not in report


def test_format_feed_check_summary_interrupted() -> None:
    now = datetime(2026, 7, 10, 12, 15, tzinfo=UTC)
    interrupted = FeedCheck(
        id=2,
        feed_type=FeedType.PRODUCT,
        status=CheckStatus.INTERRUPTED,
        started_at=now,
        finished_at=now,
        duration_seconds=21.0,
        item_count=None,
        sha256=None,
        content_size=None,
        feed_date=now,
        critical_count=0,
        warning_count=0,
        triggered_by="background",
    )
    report = format_feed_check_summary(interrupted)
    assert "прервана" in report
    assert "проверка прервана до завершения" in report


def test_format_check_cycle_completed() -> None:
    results = [_sample_check(FeedType.PRODUCT, 500), _sample_check(FeedType.STORE, 20)]
    text = format_check_cycle_completed(results, 300.0)
    assert "500" in text
    assert "20" in text
    assert "5 мин 0 сек" in text
