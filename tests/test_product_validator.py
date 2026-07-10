"""Тесты валидации товаров."""

import pytest

from app.core.config import Settings
from app.domain.enums import FeedType, IssueCategory
from app.infrastructure.xml.extractors import FeedExtractor, ProductItem
from app.infrastructure.xml.parser import ParsedFeed
from app.services.monitoring.category_validator import CategoryValidator
from app.services.monitoring.image_checker import ImageChecker
from app.services.monitoring.product_validator import ProductValidator
from tests.product_helpers import make_product
from lxml import etree


class _StubResourceChecker:
    async def check_url(self, url: str):
        raise NotImplementedError


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
    return Settings()


def _product_validator(settings: Settings) -> ProductValidator:
    resource_checker = _StubResourceChecker()
    return ProductValidator(
        resource_checker,
        ImageChecker(resource_checker, settings),
        FeedExtractor(),
        CategoryValidator(),
        settings,
    )


@pytest.mark.asyncio
async def test_missing_category_creates_alertable_issue(settings: Settings) -> None:
    validator = _product_validator(settings)
    product = make_product("100", category_id="")
    parsed = ParsedFeed(root=etree.Element("yml_catalog"), feed_date=None, raw_date=None)

    issues = await validator.validate(parsed, [product], skip_http=True)
    category_issues = [issue for issue in issues if issue.context.get("field") == "categoryId"]

    assert len(category_issues) == 1
    issue = category_issues[0]
    assert issue.message_key == "PRODUCT_MISSING_CATEGORY"
    assert issue.category == IssueCategory.MISSING_FIELD
    assert issue.feed_type == FeedType.PRODUCT
    assert issue.context["id"] == "100"


@pytest.mark.asyncio
async def test_missing_name_creates_critical_issue(settings: Settings) -> None:
    validator = _product_validator(settings)
    product = make_product("200", name="", url="https://mczgold.ru/catalog/item_200.html")
    product.name_source = None
    parsed = ParsedFeed(root=etree.Element("yml_catalog"), feed_date=None, raw_date=None)

    issues = await validator.validate(parsed, [product], skip_http=True)
    name_issues = [issue for issue in issues if issue.message_key == "PRODUCT_MISSING_NAME"]

    assert len(name_issues) == 1
    issue = name_issues[0]
    assert issue.severity.value == "critical"
    assert issue.context["id"] == "200"
    assert issue.context["url"] == product.url


@pytest.mark.asyncio
async def test_whitespace_only_name_creates_warning(settings: Settings) -> None:
    validator = _product_validator(settings)
    product = make_product("201", name="")
    product.name_source = "   "
    parsed = ParsedFeed(root=etree.Element("yml_catalog"), feed_date=None, raw_date=None)

    issues = await validator.validate(parsed, [product], skip_http=True)
    name_issues = [issue for issue in issues if issue.message_key == "PRODUCT_INVALID_NAME"]

    assert len(name_issues) == 1
    issue = name_issues[0]
    assert issue.severity.value == "warning"
    assert issue.context["name"] == "   "


@pytest.mark.asyncio
async def test_missing_url_creates_dedicated_issue(settings: Settings) -> None:
    validator = _product_validator(settings)
    product = make_product("300", url="", url_source="")
    parsed = ParsedFeed(root=etree.Element("yml_catalog"), feed_date=None, raw_date=None)

    issues = await validator.validate(parsed, [product], skip_http=True)
    url_issues = [issue for issue in issues if issue.message_key == "PRODUCT_MISSING_URL"]

    assert len(url_issues) == 1
    assert url_issues[0].category.value == "missing_url"


@pytest.mark.asyncio
async def test_duplicate_urls_create_issue(settings: Settings) -> None:
    validator = _product_validator(settings)
    products = [
        make_product("401", url="https://mczgold.ru/catalog/same.html"),
        make_product("402", url="https://mczgold.ru/catalog/same.html"),
    ]
    parsed = ParsedFeed(root=etree.Element("yml_catalog"), feed_date=None, raw_date=None)

    issues = await validator.validate(parsed, products, skip_http=True)
    duplicate_issues = [issue for issue in issues if issue.message_key == "DUPLICATE_URLS"]

    assert len(duplicate_issues) == 1
    assert duplicate_issues[0].context["count"] == 2
