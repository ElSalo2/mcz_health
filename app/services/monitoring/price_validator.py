"""Проверка корректности и аномалий цен товаров."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from app.core.config import Settings
from app.domain.entities.issue import Issue
from app.domain.enums import FeedType, IssueCategory, Severity
from app.infrastructure.xml.extractors import ProductItem
from app.services.monitoring.issue_registry import IssueRegistry


@dataclass(slots=True)
class PriceValidationResult:
    """Результат проверки цен товаров."""

    checked_count: int
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    anomalous_offer_ids: list[str] = field(default_factory=list)
    valid_prices: dict[str, Decimal] = field(default_factory=dict)

    @property
    def issues(self) -> list[Issue]:
        return self.errors + self.warnings


def parse_price_value(raw: str | None) -> Decimal | None:
    """Преобразует строковое значение цены в Decimal или возвращает None."""
    if raw is None:
        return None
    text = raw.strip().replace(" ", "").replace(",", ".")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def format_price_value(value: Decimal) -> str:
    """Форматирует цену для отображения в сообщениях."""
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


class PriceValidator:
    """Проверяет цены товаров без привязки к XML-парсеру."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def validate(
        self,
        products: list[ProductItem],
        previous_prices: dict[str, Decimal] | None = None,
    ) -> PriceValidationResult:
        """Выполняет все проверки цен для списка товаров."""
        previous = previous_prices or {}
        errors: list[Issue] = []
        warnings: list[Issue] = []
        anomalous: set[str] = set()
        valid_prices: dict[str, Decimal] = {}

        for product in products:
            product_errors, product_warnings, parsed_price = self._validate_product(
                product,
                previous,
            )
            errors.extend(product_errors)
            warnings.extend(product_warnings)
            if product_errors or product_warnings:
                if product.offer_id:
                    anomalous.add(product.offer_id)
            if parsed_price is not None and product.offer_id:
                valid_prices[product.offer_id] = parsed_price

        return PriceValidationResult(
            checked_count=len(products),
            errors=errors,
            warnings=warnings,
            anomalous_offer_ids=sorted(anomalous),
            valid_prices=valid_prices,
        )

    def _validate_product(
        self,
        product: ProductItem,
        previous_prices: dict[str, Decimal],
    ) -> tuple[list[Issue], list[Issue], Decimal | None]:
        errors: list[Issue] = []
        warnings: list[Issue] = []
        display_name = product.name or product.offer_id or "товар"
        parsed_price = parse_price_value(product.price_source)

        if product.price_source is None or parsed_price is None:
            errors.append(
                self._missing_price_issue(product, display_name),
            )
            return errors, warnings, None

        if parsed_price <= 0:
            errors.append(
                self._invalid_price_issue(product, display_name, parsed_price),
            )
            return errors, warnings, None

        price_text = format_price_value(parsed_price)

        if parsed_price < self._settings.min_product_price_warning:
            warnings.append(
                self._low_price_issue(product, display_name, price_text),
            )

        if product.oldprice_source is not None:
            parsed_oldprice = parse_price_value(product.oldprice_source)
            if parsed_oldprice is not None and parsed_oldprice <= parsed_price:
                warnings.append(
                    self._invalid_oldprice_issue(
                        product,
                        display_name,
                        price_text,
                        format_price_value(parsed_oldprice),
                    )
                )

        previous_price = previous_prices.get(product.offer_id)
        if previous_price is not None and previous_price > 0:
            change_percent = abs((parsed_price - previous_price) / previous_price * Decimal(100))
            if change_percent > Decimal(self._settings.max_price_change_percent):
                warnings.append(
                    self._price_change_issue(
                        product,
                        display_name,
                        format_price_value(previous_price),
                        price_text,
                        change_percent,
                    )
                )

        return errors, warnings, parsed_price

    def _missing_price_issue(self, product: ProductItem, display_name: str) -> Issue:
        return Issue(
            fingerprint=IssueRegistry.build_fingerprint(
                IssueCategory.PRICE_MISSING,
                FeedType.PRODUCT,
                object_id=product.offer_id,
                field="price",
            ),
            severity=Severity.CRITICAL,
            category=IssueCategory.PRICE_MISSING,
            feed_type=FeedType.PRODUCT,
            message_key="PRODUCT_MISSING_PRICE",
            object_id=product.offer_id,
            object_name=display_name,
            context={
                "name": display_name,
                "id": product.offer_id or "—",
                "url": product.url or "—",
            },
        )

    def _invalid_price_issue(
        self,
        product: ProductItem,
        display_name: str,
        price: Decimal,
    ) -> Issue:
        price_text = format_price_value(price)
        return Issue(
            fingerprint=IssueRegistry.build_fingerprint(
                IssueCategory.PRICE_INVALID,
                FeedType.PRODUCT,
                object_id=product.offer_id,
                field="price",
            ),
            severity=Severity.CRITICAL,
            category=IssueCategory.PRICE_INVALID,
            feed_type=FeedType.PRODUCT,
            message_key="PRODUCT_INVALID_PRICE",
            object_id=product.offer_id,
            object_name=display_name,
            context={
                "name": display_name,
                "id": product.offer_id or "—",
                "price": price_text,
            },
        )

    def _low_price_issue(
        self,
        product: ProductItem,
        display_name: str,
        price_text: str,
    ) -> Issue:
        return Issue(
            fingerprint=IssueRegistry.build_fingerprint(
                IssueCategory.PRICE_TOO_LOW,
                FeedType.PRODUCT,
                object_id=product.offer_id,
                field="price",
            ),
            severity=Severity.WARNING,
            category=IssueCategory.PRICE_TOO_LOW,
            feed_type=FeedType.PRODUCT,
            message_key="PRODUCT_LOW_PRICE",
            object_id=product.offer_id,
            object_name=display_name,
            context={
                "name": display_name,
                "id": product.offer_id or "—",
                "price": price_text,
            },
        )

    def _invalid_oldprice_issue(
        self,
        product: ProductItem,
        display_name: str,
        price_text: str,
        oldprice_text: str,
    ) -> Issue:
        return Issue(
            fingerprint=IssueRegistry.build_fingerprint(
                IssueCategory.PRICE_INVALID_OLDPRICE,
                FeedType.PRODUCT,
                object_id=product.offer_id,
                field="oldprice",
            ),
            severity=Severity.WARNING,
            category=IssueCategory.PRICE_INVALID_OLDPRICE,
            feed_type=FeedType.PRODUCT,
            message_key="PRODUCT_INVALID_OLDPRICE",
            object_id=product.offer_id,
            object_name=display_name,
            context={
                "name": display_name,
                "id": product.offer_id or "—",
                "price": price_text,
                "oldprice": oldprice_text,
            },
        )

    def _price_change_issue(
        self,
        product: ProductItem,
        display_name: str,
        previous_price_text: str,
        current_price_text: str,
        change_percent: Decimal,
    ) -> Issue:
        percent_text = format_price_value(change_percent.quantize(Decimal("0.1")))
        return Issue(
            fingerprint=IssueRegistry.build_fingerprint(
                IssueCategory.PRICE_CHANGE,
                FeedType.PRODUCT,
                object_id=product.offer_id,
                field="price",
            ),
            severity=Severity.WARNING,
            category=IssueCategory.PRICE_CHANGE,
            feed_type=FeedType.PRODUCT,
            message_key="PRODUCT_PRICE_CHANGE",
            object_id=product.offer_id,
            object_name=display_name,
            context={
                "name": display_name,
                "id": product.offer_id or "—",
                "old_price": previous_price_text,
                "price": current_price_text,
                "percent": percent_text,
            },
        )
