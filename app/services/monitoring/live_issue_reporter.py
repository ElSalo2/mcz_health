"""Немедленная регистрация проблем и отправка алертов во время проверки."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.entities.issue import Issue
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.services.monitoring.alert_policy import should_alert_issue
from app.services.monitoring.issue_registry import IssueRegistry
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

IMMEDIATE_HTTP_ALERT_KEYS = frozenset(
    {
        "XML_UNAVAILABLE",
        "XML_ERROR",
        "PRODUCT_PAGE_UNAVAILABLE",
        "PRODUCT_IMAGE_UNAVAILABLE",
        "STORE_IMAGE_UNAVAILABLE",
    }
)


class LiveIssueReporter:
    """Сохраняет проблему в БД и сразу шлёт Telegram-алерт, если это новая HTTP-ошибка."""

    def __init__(
        self,
        session_factory: async_sessionmaker,
        notification_service: NotificationService,
    ) -> None:
        self._session_factory = session_factory
        self._notification_service = notification_service

    async def report_http_issue(self, issue: Issue) -> None:
        """Регистрирует HTTP-проблему и уведомляет пользователей без ожидания конца цикла."""
        if issue.message_key not in IMMEDIATE_HTTP_ALERT_KEYS:
            return
        if not should_alert_issue(issue):
            return

        async with UnitOfWork(self._session_factory) as uow:
            registry = IssueRegistry(uow.errors)
            result = await registry.update(issue.feed_type, [issue])

        if not result.new_issues:
            return

        await self._notification_service.notify_new_issues(result.new_issues)
        logger.info(
            "Немедленный алерт: %s (%s)",
            issue.message_key,
            issue.object_id or issue.fingerprint[:8],
        )
