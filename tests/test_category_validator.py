"""Тесты проверки дерева категорий."""

from app.domain.enums import FeedType, IssueCategory, Severity
from app.infrastructure.xml.extractors import CategoryItem, ProductItem
from app.services.monitoring.alert_policy import should_alert_issue
from app.services.monitoring.category_validator import CategoryValidator


from tests.product_helpers import make_product


def _category(category_id: str, name: str, parent_id: str | None = None) -> CategoryItem:
    return CategoryItem(category_id=category_id, name=name, parent_id=parent_id)


def _product(offer_id: str, category_id: str) -> ProductItem:
    return make_product(offer_id, category_id=category_id)


def test_invalid_parent_missing_in_tree() -> None:
    validator = CategoryValidator()
    categories = [
        _category("1", "Корень"),
        _category("123", "Кольца", "999999"),
    ]

    issues = validator.validate(categories, [_product("1", "1")])
    parent_issues = [issue for issue in issues if issue.category == IssueCategory.INVALID_CATEGORY_PARENT]

    assert len(parent_issues) == 1
    issue = parent_issues[0]
    assert issue.message_key == "CATEGORY_INVALID_PARENT"
    assert issue.severity == Severity.CRITICAL
    assert issue.category == IssueCategory.INVALID_CATEGORY_PARENT
    assert issue.context["category_id"] == "123"
    assert issue.context["category_name"] == "Кольца"
    assert issue.context["parent_id"] == "999999"
    assert "отсутствует" in issue.context["reason"]
    assert should_alert_issue(issue)


def test_invalid_parent_self_reference() -> None:
    validator = CategoryValidator()
    categories = [
        _category("1", "Корень"),
        _category("123", "Кольца", "123"),
    ]

    issues = validator.validate(categories, [_product("1", "1")])
    parent_issues = [issue for issue in issues if issue.category == IssueCategory.INVALID_CATEGORY_PARENT]

    assert len(parent_issues) == 1
    issue = parent_issues[0]
    assert issue.message_key == "CATEGORY_INVALID_PARENT"
    assert "сама на себя" in issue.context["reason"]


def test_empty_leaf_category_without_products() -> None:
    validator = CategoryValidator()
    categories = [
        _category("1", "Корень"),
        _category("5", "Кольца", "1"),
        _category("99", "Пустая конечная", "1"),
    ]
    products = [_product("100", "5")]

    issues = validator.validate(categories, products)
    empty_issues = [issue for issue in issues if issue.category == IssueCategory.EMPTY_CATEGORY]

    assert len(empty_issues) == 1
    issue = empty_issues[0]
    assert issue.message_key == "CATEGORY_EMPTY"
    assert issue.severity == Severity.WARNING
    assert issue.context["id"] == "99"
    assert issue.context["name"] == "Пустая конечная"
    assert not should_alert_issue(issue)


def test_parent_category_without_products_is_not_error() -> None:
    validator = CategoryValidator()
    categories = [
        _category("1", "Корень"),
        _category("2", "Аксессуары", "1"),
        _category("5", "Кольца", "2"),
    ]
    products = [_product("100", "5")]

    issues = validator.validate(categories, products)

    assert issues == []


def test_valid_parent_reference() -> None:
    validator = CategoryValidator()
    categories = [
        _category("1", "Корень"),
        _category("5", "Кольца", "1"),
    ]
    products = [_product("100", "5")]

    assert validator.validate(categories, products) == []


def test_invalid_product_category_not_in_tree() -> None:
    validator = CategoryValidator()
    categories = [
        _category("1", "Корень"),
        _category("5", "Кольца", "1"),
    ]
    products = [_product("100", "999")]

    issues = validator.validate(categories, products)
    invalid_issues = [issue for issue in issues if issue.message_key == "PRODUCT_INVALID_CATEGORY"]

    assert len(invalid_issues) == 1
    issue = invalid_issues[0]
    assert issue.category == IssueCategory.INVALID_PRODUCT_CATEGORY
    assert issue.severity == Severity.CRITICAL
    assert should_alert_issue(issue)
