"""Политика отправки алертов пользователям."""

from __future__ import annotations

from app.domain.entities.issue import Issue

CRITICAL_ALERT_KEYS = frozenset(
    {
        "XML_UNAVAILABLE",
        "XML_ERROR",
        "PRODUCT_PAGE_UNAVAILABLE",
        "PRODUCT_IMAGE_UNAVAILABLE",
        "STORE_IMAGE_UNAVAILABLE",
        "PRODUCT_MISSING_PICTURE",
        "STORE_MISSING_PHOTO",
        "PRODUCT_MISSING_CATEGORY",
        "PRODUCT_INVALID_CATEGORY",
        "PRODUCT_MISSING_NAME",
        "PRODUCT_MISSING_PRICE",
        "PRODUCT_INVALID_PRICE",
        "CATEGORY_INVALID_PARENT",
        "DUPLICATE_IDS",
    }
)

WARNING_ALERT_KEYS = frozenset(
    {
        "COUNT_CHANGE",
        "FEED_SIZE_CHANGE",
        "STALE_DATA",
        "PRODUCT_LOW_PRICE",
        "PRODUCT_INVALID_OLDPRICE",
    }
)

NO_TELEGRAM_KEYS = frozenset(
    {
        "PRODUCT_PRICE_CHANGE",
        "PRODUCT_IMAGE_INVALID_CONTENT_TYPE",
        "PRODUCT_IMAGE_EMPTY",
        "STORE_IMAGE_INVALID_CONTENT_TYPE",
    }
)

HTTP_STATUS_GATED_KEYS = frozenset(
    {
        "XML_UNAVAILABLE",
        "PRODUCT_PAGE_UNAVAILABLE",
        "PRODUCT_IMAGE_UNAVAILABLE",
        "STORE_IMAGE_UNAVAILABLE",
    }
)


def _parse_http_status(status: object) -> int | None:
    if status is None:
        return None
    if isinstance(status, int):
        return status
    text = str(status).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _is_http_client_or_server_error(status_code: int | None) -> bool:
    """HTTP 4xx и 5xx."""
    return status_code is not None and 400 <= status_code < 600


def should_alert_issue(issue: Issue) -> bool:
    """Определяет, нужно ли отправлять проблему в Telegram."""
    message_key = issue.message_key

    if message_key in NO_TELEGRAM_KEYS:
        return False

    if message_key in HTTP_STATUS_GATED_KEYS:
        status_code = _parse_http_status(issue.context.get("status"))
        return _is_http_client_or_server_error(status_code)

    return message_key in CRITICAL_ALERT_KEYS or message_key in WARNING_ALERT_KEYS


def filter_alert_issues(issues: list[Issue]) -> list[Issue]:
    """Оставляет только проблемы, по которым нужно уведомлять пользователей."""
    return [issue for issue in issues if should_alert_issue(issue)]
