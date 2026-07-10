"""Тесты проверки цен товаров."""

from decimal import Decimal

import pytest

from app.core.config import Settings
from app.domain.enums import IssueCategory, Severity
from app.infrastructure.xml.extractors import ProductItem
from app.services.monitoring.alert_policy import should_alert_issue
from app.services.monitoring.price_validator import PriceValidator, parse_price_value


from tests.product_helpers import make_product


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
    monkeypatch.setenv("MIN_PRODUCT_PRICE_WARNING", "100")
    monkeypatch.setenv("MAX_PRICE_CHANGE_PERCENT", "50")
    return Settings()


def _product(
    offer_id: str,
    *,
    price_source: str | None = "1000",
    oldprice_source: str | None = None,
    name: str = "Кольцо",
) -> ProductItem:
    return make_product(
        offer_id,
        name=name,
        price_source=price_source,
        oldprice_source=oldprice_source,
    )


def test_parse_price_value_supports_decimal_formats() -> None:
    assert parse_price_value("1000") == Decimal("1000")
    assert parse_price_value("1 000,50") == Decimal("1000.50")
    assert parse_price_value("abc") is None
    assert parse_price_value(None) is None


def test_missing_price_creates_critical_issue(settings: Settings) -> None:
    validator = PriceValidator(settings)
    result = validator.validate([_product("1", price_source=None)])

    assert result.checked_count == 1
    assert len(result.errors) == 1
    assert result.warnings == []
    assert result.anomalous_offer_ids == ["1"]

    issue = result.errors[0]
    assert issue.message_key == "PRODUCT_MISSING_PRICE"
    assert issue.category == IssueCategory.PRICE_MISSING
    assert issue.severity == Severity.CRITICAL
    assert should_alert_issue(issue)


def test_invalid_non_numeric_price(settings: Settings) -> None:
    validator = PriceValidator(settings)
    result = validator.validate([_product("2", price_source="not-a-price")])

    assert len(result.errors) == 1
    assert result.errors[0].message_key == "PRODUCT_MISSING_PRICE"


def test_zero_price_creates_critical_issue(settings: Settings) -> None:
    validator = PriceValidator(settings)
    result = validator.validate([_product("3", price_source="0")])

    assert len(result.errors) == 1
    issue = result.errors[0]
    assert issue.message_key == "PRODUCT_INVALID_PRICE"
    assert issue.category == IssueCategory.PRICE_INVALID
    assert issue.context["price"] == "0"
    assert should_alert_issue(issue)


def test_negative_price_creates_critical_issue(settings: Settings) -> None:
    validator = PriceValidator(settings)
    result = validator.validate([_product("4", price_source="-10")])

    assert len(result.errors) == 1
    assert result.errors[0].message_key == "PRODUCT_INVALID_PRICE"


def test_low_price_creates_warning(settings: Settings) -> None:
    validator = PriceValidator(settings)
    result = validator.validate([_product("5", price_source="50")])

    assert result.errors == []
    assert len(result.warnings) == 1
    issue = result.warnings[0]
    assert issue.message_key == "PRODUCT_LOW_PRICE"
    assert issue.category == IssueCategory.PRICE_TOO_LOW
    assert issue.context["price"] == "50"
    assert should_alert_issue(issue)
    assert "5" in result.anomalous_offer_ids
    assert result.valid_prices["5"] == Decimal("50")


def test_invalid_oldprice_creates_warning(settings: Settings) -> None:
    validator = PriceValidator(settings)
    result = validator.validate(
        [_product("6", price_source="9000", oldprice_source="7000")],
    )

    assert result.errors == []
    assert len(result.warnings) == 1
    issue = result.warnings[0]
    assert issue.message_key == "PRODUCT_INVALID_OLDPRICE"
    assert issue.context["price"] == "9000"
    assert issue.context["oldprice"] == "7000"


def test_valid_oldprice_does_not_warn(settings: Settings) -> None:
    validator = PriceValidator(settings)
    result = validator.validate(
        [_product("7", price_source="8000", oldprice_source="10000")],
    )

    assert result.errors == []
    assert result.warnings == []


def test_price_change_above_threshold_creates_warning(settings: Settings) -> None:
    validator = PriceValidator(settings)
    previous_prices = {"8": Decimal("1000")}
    result = validator.validate(
        [_product("8", price_source="2000")],
        previous_prices,
    )

    assert result.errors == []
    assert len(result.warnings) == 1
    issue = result.warnings[0]
    assert issue.message_key == "PRODUCT_PRICE_CHANGE"
    assert issue.category == IssueCategory.PRICE_CHANGE
    assert issue.context["old_price"] == "1000"
    assert issue.context["price"] == "2000"
    assert issue.context["percent"] == "100"


def test_price_change_below_threshold_is_ignored(settings: Settings) -> None:
    validator = PriceValidator(settings)
    previous_prices = {"9": Decimal("1000")}
    result = validator.validate(
        [_product("9", price_source="1400")],
        previous_prices,
    )

    assert result.warnings == []


def test_valid_price_is_saved_for_history(settings: Settings) -> None:
    validator = PriceValidator(settings)
    result = validator.validate([_product("10", price_source="1500")])

    assert result.valid_prices == {"10": Decimal("1500")}
