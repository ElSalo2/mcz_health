"""Реестр ошибок: регистрация, дедупликация, устранение."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from app.domain.entities.issue import ActiveError, Issue
from app.domain.enums import ErrorEventType, FeedType, IssueCategory
from app.infrastructure.database.repositories.error_repository import ErrorRepository
from app.services.monitoring.alert_context import check_datetime

logger = logging.getLogger(__name__)

CATEGORY_MESSAGE_KEY: dict[IssueCategory, str] = {
    IssueCategory.FEED_UNAVAILABLE: "XML_UNAVAILABLE",
    IssueCategory.FEED_PARSE: "XML_ERROR",
    IssueCategory.MISSING_FIELD: "MISSING_REQUIRED_FIELD",
    IssueCategory.DUPLICATE_ID: "DUPLICATE_IDS",
    IssueCategory.URL_UNAVAILABLE: "PRODUCT_PAGE_UNAVAILABLE",
    IssueCategory.IMAGE_UNAVAILABLE: "PRODUCT_IMAGE_UNAVAILABLE",
    IssueCategory.INVALID_CATEGORY_PARENT: "CATEGORY_INVALID_PARENT",
    IssueCategory.INVALID_PRODUCT_CATEGORY: "PRODUCT_INVALID_CATEGORY",
    IssueCategory.PRICE_MISSING: "PRODUCT_MISSING_PRICE",
    IssueCategory.PRICE_INVALID: "PRODUCT_INVALID_PRICE",
}


@dataclass(slots=True)
class RegistryResult:
    """Результат обновления реестра ошибок."""

    new_issues: list[Issue]
    resolved_issues: list[Issue]
    unchanged_count: int


class IssueRegistry:
    """Управляет жизненным циклом ошибок и дедупликацией уведомлений."""

    def __init__(self, error_repository: ErrorRepository) -> None:
        self._error_repository = error_repository

    @staticmethod
    def build_fingerprint(
        category: IssueCategory,
        feed_type: FeedType,
        object_id: str | None = None,
        field: str | None = None,
        url: str | None = None,
    ) -> str:
        """Создаёт уникальный отпечаток ошибки."""
        parts = [category.value, feed_type.value, object_id or "", field or "", url or ""]
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()

    async def update(self, feed_type: FeedType, current_issues: list[Issue]) -> RegistryResult:
        """Сравнивает текущие ошибки с активными и обновляет реестр."""
        active_errors = await self._error_repository.get_active_errors(feed_type)
        active_map = {error.fingerprint: error for error in active_errors}
        current_map = {issue.fingerprint: issue for issue in current_issues}

        new_issues: list[Issue] = []
        resolved_issues: list[Issue] = []
        unchanged_count = 0

        for fingerprint, issue in current_map.items():
            if fingerprint in active_map:
                await self._error_repository.upsert_active_error(issue)
                unchanged_count += 1
            else:
                await self._error_repository.upsert_active_error(issue, notified=False)
                await self._error_repository.add_history_event(
                    fingerprint=fingerprint,
                    event_type=ErrorEventType.OPENED,
                    context=issue.context,
                )
                new_issues.append(issue)

        for fingerprint, active_error in active_map.items():
            if fingerprint not in current_map:
                await self._error_repository.resolve_error(
                    fingerprint,
                    context={"resolved_from": feed_type.value},
                )
                resolved_issues.append(self._active_error_to_issue(active_error))

        return RegistryResult(
            new_issues=new_issues,
            resolved_issues=resolved_issues,
            unchanged_count=unchanged_count,
        )

    @staticmethod
    def _resolve_object_label(context: dict[str, object], active_error: ActiveError) -> str:
        for key in ("name", "offer_id", "id", "feed_name", "category_id", "field"):
            value = context.get(key)
            if value not in (None, ""):
                return str(value)
        return active_error.fingerprint

    @classmethod
    def _active_error_to_issue(cls, active_error: ActiveError) -> Issue:
        context = dict(active_error.context_json)
        original_key = str(context.get("message_key") or CATEGORY_MESSAGE_KEY.get(active_error.category, ""))
        object_label = cls._resolve_object_label(context, active_error)
        return Issue(
            fingerprint=active_error.fingerprint,
            severity=active_error.severity,
            category=active_error.category,
            feed_type=active_error.feed_type,
            message_key="ISSUE_RESOLVED",
            context={
                "error_code": original_key,
                "message_key": original_key,
                "object": object_label,
                "description": "Проблема больше не воспроизводится при повторной проверке",
                "datetime": check_datetime(),
                "notified": active_error.notified,
            },
            object_name=str(context.get("name") or "") or None,
        )
