"""Этап 3: валидация товаров."""

from __future__ import annotations

import logging
from collections import Counter

from app.bot.formatters.check_formatter import format_datetime_moscow, format_feed_date
from app.core.config import Settings
from app.domain.entities.issue import Issue
from app.domain.enums import FeedType, IssueCategory, Severity
from app.domain.validators.product_rules import PRODUCT_REQUIRED_FIELDS
from app.infrastructure.database.utils import utc_now
from app.infrastructure.http.resource_checker import ResourceChecker
from app.infrastructure.xml.extractors import FeedExtractor, ProductItem
from app.infrastructure.xml.parser import ParsedFeed
from app.services.monitoring.alert_context import format_duplicate_values
from app.services.monitoring.category_validator import CategoryValidator
from app.services.monitoring.image_checker import ImageChecker
from app.services.monitoring.issue_registry import IssueRegistry

logger = logging.getLogger(__name__)


class ProductValidator:
    """Проверяет содержимое фида товаров."""

    def __init__(
        self,
        resource_checker: ResourceChecker,
        image_checker: ImageChecker,
        feed_extractor: FeedExtractor,
        category_validator: CategoryValidator,
        settings: Settings,
    ) -> None:
        self._resource_checker = resource_checker
        self._image_checker = image_checker
        self._feed_extractor = feed_extractor
        self._category_validator = category_validator
        self._settings = settings

    async def validate(
        self,
        parsed: ParsedFeed,
        products: list[ProductItem],
        *,
        skip_http: bool = False,
    ) -> list[Issue]:
        """Выполняет все проверки товаров."""
        issues: list[Issue] = []
        issues.extend(self._check_duplicate_ids(products))
        issues.extend(self._check_duplicate_urls(products))
        categories = self._feed_extractor.extract_categories(parsed.root)
        issues.extend(self._category_validator.validate(categories, products))
        feed_date = format_feed_date(parsed.feed_date) if parsed.feed_date else None
        check_date = format_datetime_moscow(utc_now())

        for product in products:
            issues.extend(self._check_product_name(product))
            issues.extend(self._check_missing_url(product))
            issues.extend(self._check_required_fields(product))
            if skip_http:
                continue

            if product.url:
                response = await self._resource_checker.check_url(product.url, kind="product_page")
                if response.status_code is None or response.status_code >= 400:
                    status = (
                        str(response.status_code)
                        if response.status_code is not None
                        else (response.error or "ошибка")
                    )
                    issues.append(
                        Issue(
                            fingerprint=IssueRegistry.build_fingerprint(
                                IssueCategory.URL_UNAVAILABLE,
                                FeedType.PRODUCT,
                                object_id=product.offer_id,
                                url=product.url,
                            ),
                            severity=Severity.CRITICAL,
                            category=IssueCategory.URL_UNAVAILABLE,
                            feed_type=FeedType.PRODUCT,
                            message_key="PRODUCT_PAGE_UNAVAILABLE",
                            object_id=product.offer_id,
                            object_name=product.name,
                            context={
                                "id": product.offer_id,
                                "name": product.name,
                                "url": product.url,
                                "status": status,
                                "feed_date": feed_date or "—",
                                "check_date": check_date,
                            },
                        )
                    )

            if self._settings.should_check_images("product"):
                issues.extend(
                    await self._image_checker.check_images(
                        product.pictures,
                        product.offer_id,
                        product.name,
                        FeedType.PRODUCT,
                        feed_date=feed_date,
                        product_url=product.url,
                    )
                )

        return issues

    def _check_product_name(self, product: ProductItem) -> list[Issue]:
        """Проверяет обязательное поле name."""
        if product.name_source is None or product.name_source == "":
            return [
                Issue(
                    fingerprint=IssueRegistry.build_fingerprint(
                        IssueCategory.MISSING_FIELD,
                        FeedType.PRODUCT,
                        object_id=product.offer_id,
                        field="name",
                    ),
                    severity=Severity.CRITICAL,
                    category=IssueCategory.MISSING_FIELD,
                    feed_type=FeedType.PRODUCT,
                    message_key="PRODUCT_MISSING_NAME",
                    object_id=product.offer_id,
                    object_name=product.offer_id or "товар",
                    context={
                        "id": product.offer_id or "—",
                        "url": product.url or "—",
                        "field": "name",
                    },
                )
            ]

        if not product.name_source.strip():
            return [
                Issue(
                    fingerprint=IssueRegistry.build_fingerprint(
                        IssueCategory.INVALID_PRODUCT_NAME,
                        FeedType.PRODUCT,
                        object_id=product.offer_id,
                        field="name",
                    ),
                    severity=Severity.WARNING,
                    category=IssueCategory.INVALID_PRODUCT_NAME,
                    feed_type=FeedType.PRODUCT,
                    message_key="PRODUCT_INVALID_NAME",
                    object_id=product.offer_id,
                    object_name=product.offer_id or "товар",
                    context={
                        "id": product.offer_id or "—",
                        "name": product.name_source,
                        "field": "name",
                    },
                )
            ]

        return []

    def _check_required_fields(self, product: ProductItem) -> list[Issue]:
        issues: list[Issue] = []
        values = {
            "id": product.offer_id,
            "vendor": product.vendor,
            "picture": product.pictures[0] if product.pictures else "",
            "categoryId": product.category_id,
        }
        for field in PRODUCT_REQUIRED_FIELDS:
            if not str(values.get(field, "")).strip():
                issues.append(self._missing_field_issue(product, field))
        return issues

    def _check_duplicate_ids(self, products: list[ProductItem]) -> list[Issue]:
        counter = Counter(product.offer_id for product in products if product.offer_id)
        duplicates = {offer_id: count for offer_id, count in counter.items() if count > 1}
        if not duplicates:
            return []

        offer_id, count = next(iter(duplicates.items()))
        return [
            Issue(
                fingerprint=IssueRegistry.build_fingerprint(
                    IssueCategory.DUPLICATE_ID,
                    FeedType.PRODUCT,
                    field="id",
                ),
                severity=Severity.CRITICAL,
                category=IssueCategory.DUPLICATE_ID,
                feed_type=FeedType.PRODUCT,
                message_key="DUPLICATE_IDS",
                context={
                    "object_type": "товары",
                    "field": "id",
                    "count": str(len(duplicates)),
                    "duplicates": format_duplicate_values(duplicates),
                },
            )
        ]

    def _check_missing_url(self, product: ProductItem) -> list[Issue]:
        if product.url_source is not None and product.url_source.strip():
            return []

        display_name = product.name or product.offer_id or "товар"
        return [
            Issue(
                fingerprint=IssueRegistry.build_fingerprint(
                    IssueCategory.MISSING_URL,
                    FeedType.PRODUCT,
                    object_id=product.offer_id,
                    field="url",
                ),
                severity=Severity.CRITICAL,
                category=IssueCategory.MISSING_URL,
                feed_type=FeedType.PRODUCT,
                message_key="PRODUCT_MISSING_URL",
                object_id=product.offer_id,
                object_name=display_name,
                context={
                    "name": display_name,
                    "id": product.offer_id or "—",
                },
            )
        ]

    def _check_duplicate_urls(self, products: list[ProductItem]) -> list[Issue]:
        counter = Counter(product.url for product in products if product.url)
        duplicates = {url: count for url, count in counter.items() if count > 1}
        if not duplicates:
            return []

        url, count = next(iter(duplicates.items()))
        return [
            Issue(
                fingerprint=IssueRegistry.build_fingerprint(
                    IssueCategory.DUPLICATE_URL,
                    FeedType.PRODUCT,
                    field="url",
                    url=url,
                ),
                severity=Severity.CRITICAL,
                category=IssueCategory.DUPLICATE_URL,
                feed_type=FeedType.PRODUCT,
                message_key="DUPLICATE_URLS",
                context={"url": url, "count": count},
            )
        ]

    @staticmethod
    def _missing_field_issue(product: ProductItem, field: str) -> Issue:
        display_name = product.name or product.offer_id or "товар"
        if field == "picture":
            message_key = "PRODUCT_MISSING_PICTURE"
            context = {
                "id": product.offer_id or "—",
                "name": display_name,
                "url": product.url or "—",
                "field": field,
            }
        elif field == "categoryId":
            message_key = "PRODUCT_MISSING_CATEGORY"
            context = {
                "id": product.offer_id or "—",
                "name": display_name,
                "url": product.url or "—",
                "field": field,
            }
        else:
            message_key = "MISSING_REQUIRED_FIELD"
            context = {"name": display_name, "field": field}
        return Issue(
            fingerprint=IssueRegistry.build_fingerprint(
                IssueCategory.MISSING_FIELD,
                FeedType.PRODUCT,
                object_id=product.offer_id,
                field=field,
            ),
            severity=Severity.CRITICAL,
            category=IssueCategory.MISSING_FIELD,
            feed_type=FeedType.PRODUCT,
            message_key=message_key,
            object_id=product.offer_id,
            object_name=display_name,
            context=context,
        )
