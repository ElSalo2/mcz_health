"""Тесты политики алертов."""

from app.domain.entities.issue import Issue
from app.domain.enums import FeedType, IssueCategory, Severity
from app.services.monitoring.alert_policy import (
    CRITICAL_ALERT_KEYS,
    NO_TELEGRAM_KEYS,
    WARNING_ALERT_KEYS,
    filter_alert_issues,
    should_alert_issue,
)


def _issue(message_key: str, *, category: IssueCategory, severity: Severity, context: dict | None = None) -> Issue:
    return Issue(
        fingerprint=f"test:{message_key}",
        severity=severity,
        category=category,
        feed_type=FeedType.PRODUCT,
        message_key=message_key,
        context=context or {},
    )


def test_critical_alert_keys_are_telegraphed() -> None:
    for message_key in CRITICAL_ALERT_KEYS:
        if message_key in {
            "XML_UNAVAILABLE",
            "PRODUCT_PAGE_UNAVAILABLE",
            "PRODUCT_IMAGE_UNAVAILABLE",
            "STORE_IMAGE_UNAVAILABLE",
        }:
            issue = _issue(message_key, category=IssueCategory.URL_UNAVAILABLE, severity=Severity.CRITICAL, context={"status": 404})
        else:
            issue = _issue(message_key, category=IssueCategory.MISSING_FIELD, severity=Severity.CRITICAL)
        assert should_alert_issue(issue), message_key


def test_warning_alert_keys_are_telegraphed() -> None:
    for message_key in WARNING_ALERT_KEYS:
        issue = _issue(message_key, category=IssueCategory.STALE_DATA, severity=Severity.WARNING)
        assert should_alert_issue(issue), message_key


def test_no_telegram_keys_are_filtered() -> None:
    for message_key in NO_TELEGRAM_KEYS:
        issue = _issue(message_key, category=IssueCategory.PRICE_CHANGE, severity=Severity.WARNING)
        assert not should_alert_issue(issue), message_key


def test_http_errors_without_status_code_are_not_alerted() -> None:
    issue = _issue(
        "PRODUCT_PAGE_UNAVAILABLE",
        category=IssueCategory.URL_UNAVAILABLE,
        severity=Severity.CRITICAL,
        context={"status": "ошибка"},
    )
    assert not should_alert_issue(issue)


def test_duplicate_ids_is_alerted() -> None:
    issue = _issue(
        "DUPLICATE_IDS",
        category=IssueCategory.DUPLICATE_ID,
        severity=Severity.CRITICAL,
        context={"field": "id", "count": 2},
    )
    assert should_alert_issue(issue)


def test_report_only_issues_are_not_alerted() -> None:
    report_only = [
        _issue("PRODUCT_MISSING_URL", category=IssueCategory.MISSING_URL, severity=Severity.CRITICAL),
        _issue("DUPLICATE_URLS", category=IssueCategory.DUPLICATE_URL, severity=Severity.CRITICAL),
        _issue("PRODUCT_NEGATIVE_STOCK", category=IssueCategory.NEGATIVE_STOCK, severity=Severity.WARNING),
        _issue("PRODUCT_AVAILABLE_AT_ZERO_STOCK", category=IssueCategory.AVAILABLE_AT_ZERO_STOCK, severity=Severity.WARNING),
        _issue("PRODUCT_INVALID_NAME", category=IssueCategory.INVALID_PRODUCT_NAME, severity=Severity.WARNING),
        _issue("CATEGORY_EMPTY", category=IssueCategory.EMPTY_CATEGORY, severity=Severity.WARNING),
    ]
    for issue in report_only:
        assert not should_alert_issue(issue)


def test_filter_alert_issues() -> None:
    issues = [
        _issue("XML_ERROR", category=IssueCategory.FEED_PARSE, severity=Severity.CRITICAL),
        _issue("PRODUCT_PRICE_CHANGE", category=IssueCategory.PRICE_CHANGE, severity=Severity.WARNING),
        _issue(
            "PRODUCT_IMAGE_UNAVAILABLE",
            category=IssueCategory.IMAGE_UNAVAILABLE,
            severity=Severity.CRITICAL,
            context={"status": 500},
        ),
        _issue("COUNT_CHANGE", category=IssueCategory.COUNT_CHANGE, severity=Severity.WARNING),
    ]
    filtered = filter_alert_issues(issues)
    assert {issue.message_key for issue in filtered} == {
        "XML_ERROR",
        "PRODUCT_IMAGE_UNAVAILABLE",
        "COUNT_CHANGE",
    }
