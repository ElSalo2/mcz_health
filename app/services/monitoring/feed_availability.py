"""Этап 1: проверка доступности XML."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.config import Settings
from app.domain.entities.issue import Issue
from app.domain.enums import FeedType, IssueCategory, Severity
from app.infrastructure.http.client import HttpClient
from app.services.monitoring.feed_labels import feed_label
from app.services.monitoring.issue_registry import IssueRegistry

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AvailabilityResult:
    """Результат проверки доступности фида."""

    available: bool
    content: bytes | None
    status: str | None
    issue: Issue | None = None


class FeedAvailabilityChecker:
    """Проверяет доступность XML-фида."""

    def __init__(self, http_client: HttpClient, settings: Settings) -> None:
        self._http_client = http_client
        self._settings = settings

    async def check(self, feed_type: FeedType) -> AvailabilityResult:
        """Загружает XML и проверяет доступность."""
        url = self._settings.get_feed_url(feed_type.value)
        response = await self._http_client.get_bytes(url)

        if response.status_code is not None and response.status_code < 400 and response.content:
            return AvailabilityResult(
                available=True,
                content=response.content,
                status=str(response.status_code),
            )

        status = response.error or str(response.status_code or "недоступен")
        issue = Issue(
            fingerprint=IssueRegistry.build_fingerprint(
                IssueCategory.FEED_UNAVAILABLE,
                feed_type,
            ),
            severity=Severity.CRITICAL,
            category=IssueCategory.FEED_UNAVAILABLE,
            feed_type=feed_type,
            message_key="XML_UNAVAILABLE",
            context={
                "feed_name": feed_label(feed_type),
                "feed_url": url,
                "status": status,
            },
        )
        return AvailabilityResult(available=False, content=None, status=status, issue=issue)
