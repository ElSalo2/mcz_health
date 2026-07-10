"""Проверка дерева категорий товарного фида."""

from __future__ import annotations

from app.domain.entities.issue import Issue
from app.domain.enums import FeedType, IssueCategory, Severity
from app.infrastructure.xml.extractors import CategoryItem, ProductItem
from app.services.monitoring.issue_registry import IssueRegistry

REASON_MISSING_PARENT = "Указанная родительская категория отсутствует в дереве категорий."
REASON_SELF_PARENT = "Категория ссылается сама на себя."
REASON_EMPTY_LEAF = "Категория существует в дереве, но не связана ни с одним товаром."


class CategoryValidator:
    """Проверяет корректность дерева категорий и использование категорий товарами."""

    def validate(self, categories: list[CategoryItem], products: list[ProductItem]) -> list[Issue]:
        """Выполняет проверки структуры и заполненности категорий."""
        issues: list[Issue] = []
        issues.extend(self._check_parent_references(categories))
        issues.extend(self._check_product_category_references(categories, products))
        issues.extend(self._check_empty_leaf_categories(categories, products))
        return issues

    def _check_product_category_references(
        self,
        categories: list[CategoryItem],
        products: list[ProductItem],
    ) -> list[Issue]:
        issues: list[Issue] = []
        known_ids = {category.category_id for category in categories if category.category_id}

        for product in products:
            if not product.category_id:
                continue
            if product.category_id in known_ids:
                continue
            display_name = product.name or product.offer_id or "товар"
            issues.append(
                Issue(
                    fingerprint=IssueRegistry.build_fingerprint(
                        IssueCategory.INVALID_PRODUCT_CATEGORY,
                        FeedType.PRODUCT,
                        object_id=product.offer_id,
                        field=product.category_id,
                    ),
                    severity=Severity.CRITICAL,
                    category=IssueCategory.INVALID_PRODUCT_CATEGORY,
                    feed_type=FeedType.PRODUCT,
                    message_key="PRODUCT_INVALID_CATEGORY",
                    object_id=product.offer_id,
                    object_name=display_name,
                    context={
                        "name": display_name,
                        "id": product.offer_id or "—",
                        "category_id": product.category_id,
                    },
                )
            )

        return issues

    def _check_parent_references(self, categories: list[CategoryItem]) -> list[Issue]:
        issues: list[Issue] = []
        known_ids = {category.category_id for category in categories if category.category_id}

        for category in categories:
            if not category.parent_id:
                continue

            if category.parent_id == category.category_id:
                issues.append(
                    self._invalid_parent_issue(
                        category,
                        reason=REASON_SELF_PARENT,
                    )
                )
                continue

            if category.parent_id not in known_ids:
                issues.append(
                    self._invalid_parent_issue(
                        category,
                        reason=REASON_MISSING_PARENT,
                    )
                )

        return issues

    def _check_empty_leaf_categories(
        self,
        categories: list[CategoryItem],
        products: list[ProductItem],
    ) -> list[Issue]:
        issues: list[Issue] = []
        parent_ids = {
            category.parent_id
            for category in categories
            if category.parent_id
        }
        used_category_ids = {
            product.category_id
            for product in products
            if product.category_id
        }

        for category in categories:
            if category.category_id in parent_ids:
                continue
            if category.category_id in used_category_ids:
                continue
            issues.append(self._empty_leaf_issue(category))

        return issues

    @staticmethod
    def _invalid_parent_issue(category: CategoryItem, *, reason: str) -> Issue:
        display_name = category.name or category.category_id or "категория"
        parent_id = category.parent_id or "—"
        return Issue(
            fingerprint=IssueRegistry.build_fingerprint(
                IssueCategory.INVALID_CATEGORY_PARENT,
                FeedType.PRODUCT,
                object_id=category.category_id,
                field=parent_id,
            ),
            severity=Severity.CRITICAL,
            category=IssueCategory.INVALID_CATEGORY_PARENT,
            feed_type=FeedType.PRODUCT,
            message_key="CATEGORY_INVALID_PARENT",
            object_id=category.category_id,
            object_name=display_name,
            context={
                "category_name": display_name,
                "category_id": category.category_id or "—",
                "parent_id": parent_id,
                "reason": reason,
            },
        )

    @staticmethod
    def _empty_leaf_issue(category: CategoryItem) -> Issue:
        display_name = category.name or category.category_id or "категория"
        return Issue(
            fingerprint=IssueRegistry.build_fingerprint(
                IssueCategory.EMPTY_CATEGORY,
                FeedType.PRODUCT,
                object_id=category.category_id,
            ),
            severity=Severity.WARNING,
            category=IssueCategory.EMPTY_CATEGORY,
            feed_type=FeedType.PRODUCT,
            message_key="CATEGORY_EMPTY",
            object_id=category.category_id,
            object_name=display_name,
            context={
                "name": display_name,
                "id": category.category_id or "—",
                "reason": REASON_EMPTY_LEAF,
            },
        )
