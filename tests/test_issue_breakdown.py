"""Тесты расшифровки проблем и прогресса HTTP."""

from datetime import UTC, datetime

from app.bot.formatters.check_formatter import (
    _format_progress,
    format_issues_breakdown,
)
from app.domain.entities.feed_check import FeedCheck
from app.domain.enums import CheckStatus, FeedType
from app.domain.value_objects.check_stats import CheckStats
from app.infrastructure.database.utils import dump_json
from app.services.monitoring.issue_breakdown import count_issues_by_type
from app.domain.entities.issue import Issue
from app.domain.enums import IssueCategory, Severity


def test_format_progress_allows_over_plan() -> None:
    text = _format_progress(47195, 46782)
    assert "47 195 из 46 782" in text
    assert "101%" in text
    assert "+413 повторных URL" in text


def test_format_issues_breakdown() -> None:
    check = FeedCheck(
        id=1,
        feed_type=FeedType.PRODUCT,
        status=CheckStatus.SUCCESS,
        started_at=datetime(2026, 7, 13, 2, 20, tzinfo=UTC),
        finished_at=datetime(2026, 7, 13, 6, 19, tzinfo=UTC),
        duration_seconds=100.0,
        item_count=11373,
        sha256="hash",
        content_size=1000,
        feed_date=datetime(2026, 7, 13, 1, 50, tzinfo=UTC),
        critical_count=0,
        warning_count=2,
        triggered_by="background",
        stats_json=dump_json(
            {
                "warnings_by_type": {
                    "CATEGORY_EMPTY": 15599,
                    "PRODUCT_LOW_PRICE": 3,
                }
            }
        ),
    )
    text = format_issues_breakdown(check)
    assert "Предупреждения:" in text
    assert "Категория без товара (CATEGORY_EMPTY): 15 599" in text
    assert "подозрительно низкая цена (PRODUCT_LOW_PRICE): 3" in text


def test_count_issues_by_type() -> None:
    issues = [
        Issue(
            fingerprint="a",
            severity=Severity.WARNING,
            category=IssueCategory.EMPTY_CATEGORY,
            feed_type=FeedType.PRODUCT,
            message_key="CATEGORY_EMPTY",
            context={},
        ),
        Issue(
            fingerprint="b",
            severity=Severity.CRITICAL,
            category=IssueCategory.URL_UNAVAILABLE,
            feed_type=FeedType.PRODUCT,
            message_key="PRODUCT_PAGE_UNAVAILABLE",
            context={},
        ),
    ]
    warnings, critical = count_issues_by_type(issues)
    assert warnings == {"CATEGORY_EMPTY": 1}
    assert critical == {"PRODUCT_PAGE_UNAVAILABLE": 1}
