"""Проверка остатков и доступности товаров."""

from __future__ import annotations

from app.domain.entities.issue import Issue
from app.domain.enums import FeedType, IssueCategory, Severity
from app.infrastructure.xml.extractors import ProductItem
from app.services.monitoring.issue_registry import IssueRegistry


def parse_stock_value(raw: str | None) -> int | None:
    """Преобразует значение остатка в целое число."""
    if raw is None:
        return None
    text = raw.strip().replace(" ", "")
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def parse_available_value(raw: str | None) -> bool | None:
    """Преобразует атрибут available в bool."""
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return None


class StockValidator:
    """Проверяет остатки и флаг доступности товаров."""

    def validate(self, products: list[ProductItem]) -> list[Issue]:
        """Выполняет проверки остатков для списка товаров."""
        issues: list[Issue] = []
        for product in products:
            issues.extend(self._validate_product(product))
        return issues

    def _validate_product(self, product: ProductItem) -> list[Issue]:
        issues: list[Issue] = []
        display_name = product.name or product.offer_id or "товар"
        stock = parse_stock_value(product.stock_source)
        available = parse_available_value(product.available_source)

        if stock is not None and stock < 0:
            issues.append(
                Issue(
                    fingerprint=IssueRegistry.build_fingerprint(
                        IssueCategory.NEGATIVE_STOCK,
                        FeedType.PRODUCT,
                        object_id=product.offer_id,
                        field="count",
                    ),
                    severity=Severity.WARNING,
                    category=IssueCategory.NEGATIVE_STOCK,
                    feed_type=FeedType.PRODUCT,
                    message_key="PRODUCT_NEGATIVE_STOCK",
                    object_id=product.offer_id,
                    object_name=display_name,
                    context={
                        "name": display_name,
                        "id": product.offer_id or "—",
                        "stock": str(stock),
                    },
                )
            )

        if stock is not None and stock == 0 and available is True:
            issues.append(
                Issue(
                    fingerprint=IssueRegistry.build_fingerprint(
                        IssueCategory.AVAILABLE_AT_ZERO_STOCK,
                        FeedType.PRODUCT,
                        object_id=product.offer_id,
                        field="available",
                    ),
                    severity=Severity.WARNING,
                    category=IssueCategory.AVAILABLE_AT_ZERO_STOCK,
                    feed_type=FeedType.PRODUCT,
                    message_key="PRODUCT_AVAILABLE_AT_ZERO_STOCK",
                    object_id=product.offer_id,
                    object_name=display_name,
                    context={
                        "name": display_name,
                        "id": product.offer_id or "—",
                        "stock": "0",
                        "available": product.available_source or "true",
                    },
                )
            )

        return issues
