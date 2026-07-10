"""Тесты проверки остатков товаров."""

from app.domain.enums import IssueCategory
from app.services.monitoring.alert_policy import should_alert_issue
from app.services.monitoring.stock_validator import StockValidator, parse_available_value, parse_stock_value
from tests.product_helpers import make_product


def test_parse_stock_and_available() -> None:
    assert parse_stock_value("10") == 10
    assert parse_stock_value("-1") == -1
    assert parse_available_value("true") is True
    assert parse_available_value("false") is False


def test_negative_stock_creates_warning_without_telegram() -> None:
    validator = StockValidator()
    product = make_product("1", stock_source="-5")

    issues = validator.validate([product])

    assert len(issues) == 1
    issue = issues[0]
    assert issue.message_key == "PRODUCT_NEGATIVE_STOCK"
    assert issue.category == IssueCategory.NEGATIVE_STOCK
    assert not should_alert_issue(issue)


def test_available_at_zero_stock_creates_warning_without_telegram() -> None:
    validator = StockValidator()
    product = make_product("2", stock_source="0", available_source="true")

    issues = validator.validate([product])

    assert len(issues) == 1
    issue = issues[0]
    assert issue.message_key == "PRODUCT_AVAILABLE_AT_ZERO_STOCK"
    assert not should_alert_issue(issue)
