"""Тесты немедленных HTTP-алертов."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.entities.issue import Issue
from app.domain.enums import FeedType, IssueCategory, Severity
from app.services.monitoring.issue_registry import IssueRegistry
from app.services.monitoring.live_issue_reporter import LiveIssueReporter


@pytest.mark.asyncio
async def test_live_reporter_notifies_new_http_issue(session_factory) -> None:
    issue = Issue(
        fingerprint=IssueRegistry.build_fingerprint(
            IssueCategory.URL_UNAVAILABLE,
            FeedType.PRODUCT,
            object_id="100",
            url="https://mczgold.ru/broken.html",
        ),
        severity=Severity.CRITICAL,
        category=IssueCategory.URL_UNAVAILABLE,
        feed_type=FeedType.PRODUCT,
        message_key="PRODUCT_PAGE_UNAVAILABLE",
        object_id="100",
        object_name="Кольцо",
        context={
            "id": "100",
            "name": "Кольцо",
            "url": "https://mczgold.ru/broken.html",
            "status": "404",
        },
    )
    notification_service = MagicMock()
    notification_service.notify_new_issues = AsyncMock()
    reporter = LiveIssueReporter(session_factory, notification_service)

    await reporter.report_http_issue(issue)

    notification_service.notify_new_issues.assert_awaited_once()
    alerted = notification_service.notify_new_issues.await_args.args[0]
    assert alerted[0].message_key == "PRODUCT_PAGE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_live_reporter_skips_non_http_issues(session_factory) -> None:
    issue = Issue(
        fingerprint=IssueRegistry.build_fingerprint(
            IssueCategory.EMPTY_CATEGORY,
            FeedType.PRODUCT,
            object_id="725",
        ),
        severity=Severity.WARNING,
        category=IssueCategory.EMPTY_CATEGORY,
        feed_type=FeedType.PRODUCT,
        message_key="CATEGORY_EMPTY",
        object_id="725",
        context={"id": "725", "name": "Бриллианты"},
    )
    notification_service = MagicMock()
    notification_service.notify_new_issues = AsyncMock()
    reporter = LiveIssueReporter(session_factory, notification_service)

    await reporter.report_http_issue(issue)

    notification_service.notify_new_issues.assert_not_called()


@pytest.mark.asyncio
async def test_live_reporter_does_not_repeat_known_issue(session_factory) -> None:
    issue = Issue(
        fingerprint=IssueRegistry.build_fingerprint(
            IssueCategory.URL_UNAVAILABLE,
            FeedType.PRODUCT,
            object_id="100",
            url="https://mczgold.ru/broken.html",
        ),
        severity=Severity.CRITICAL,
        category=IssueCategory.URL_UNAVAILABLE,
        feed_type=FeedType.PRODUCT,
        message_key="PRODUCT_PAGE_UNAVAILABLE",
        object_id="100",
        context={
            "id": "100",
            "name": "Кольцо",
            "url": "https://mczgold.ru/broken.html",
            "status": "404",
        },
    )
    notification_service = MagicMock()
    notification_service.notify_new_issues = AsyncMock()
    reporter = LiveIssueReporter(session_factory, notification_service)

    await reporter.report_http_issue(issue)
    await reporter.report_http_issue(issue)

    notification_service.notify_new_issues.assert_awaited_once()
