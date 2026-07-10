"""Детектор изменений: SHA-256, счётчики и размер фида."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC

from app.bot.formatters.check_formatter import format_datetime_moscow, format_feed_date
from app.core.config import Settings
from app.domain.entities.feed_check import FeedCheck
from app.domain.entities.issue import Issue
from app.domain.enums import FeedType, IssueCategory, Severity
from app.infrastructure.database.utils import utc_now
from app.infrastructure.xml.parser import ParsedFeed
from app.services.monitoring.feed_labels import feed_label
from app.services.monitoring.issue_registry import IssueRegistry

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ChangeDetectionResult:
    """Результат сравнения с предыдущей проверкой."""

    skip_deep_check: bool
    count_changed: bool
    percent_change: float | None
    issues: list[Issue] = field(default_factory=list)


class ChangeDetector:
    """Сравнивает текущие данные с предыдущей успешной проверкой."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @staticmethod
    def compute_sha256(content: bytes) -> str:
        """Вычисляет SHA-256 хеш содержимого."""
        return hashlib.sha256(content).hexdigest()

    def detect(
        self,
        feed_type: FeedType,
        content: bytes,
        item_count: int,
        previous_check: FeedCheck | None,
    ) -> ChangeDetectionResult:
        """Определяет, нужно ли выполнять глубокую HTTP-проверку."""
        sha256 = self.compute_sha256(content)
        content_size = len(content)
        skip_deep = False
        count_changed = False
        percent_change: float | None = None
        issues: list[Issue] = []

        if previous_check is not None:
            if previous_check.sha256 == sha256 and previous_check.item_count == item_count:
                skip_deep = True

            if previous_check.item_count and previous_check.item_count > 0:
                delta = abs(item_count - previous_check.item_count)
                percent_change = round(delta / previous_check.item_count * 100, 1)
                limit = self._settings.get_count_change_limit_percent(feed_type.value)
                if percent_change > limit:
                    count_changed = True
                    issues.append(
                        Issue(
                            fingerprint=IssueRegistry.build_fingerprint(
                                IssueCategory.COUNT_CHANGE,
                                feed_type,
                            ),
                            severity=Severity.WARNING,
                            category=IssueCategory.COUNT_CHANGE,
                            feed_type=feed_type,
                            message_key="COUNT_CHANGE",
                            context={
                                "feed_type": feed_type.value,
                                "previous": str(previous_check.item_count),
                                "current": str(item_count),
                                "percent": str(percent_change),
                            },
                        )
                    )

            size_issue = self._check_feed_size_change(feed_type, content_size, previous_check)
            if size_issue is not None:
                issues.append(size_issue)

        return ChangeDetectionResult(
            skip_deep_check=skip_deep,
            count_changed=count_changed,
            percent_change=percent_change,
            issues=issues,
        )

    def _check_feed_size_change(
        self,
        feed_type: FeedType,
        content_size: int,
        previous_check: FeedCheck,
    ) -> Issue | None:
        previous_size = previous_check.content_size
        if not previous_size or previous_size <= 0:
            return None

        percent_change = round(abs(content_size - previous_size) / previous_size * 100, 1)
        if percent_change <= self._settings.max_feed_size_change_percent:
            return None

        return Issue(
            fingerprint=IssueRegistry.build_fingerprint(
                IssueCategory.FEED_SIZE_CHANGE,
                feed_type,
            ),
            severity=Severity.WARNING,
            category=IssueCategory.FEED_SIZE_CHANGE,
            feed_type=feed_type,
            message_key="FEED_SIZE_CHANGE",
            context={
                "feed_name": feed_label(feed_type),
                "previous_size": self._format_size(previous_size),
                "current_size": self._format_size(content_size),
                "percent": str(percent_change),
            },
        )

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes >= 1_048_576:
            return f"{size_bytes / 1_048_576:.2f} МБ"
        if size_bytes >= 1024:
            return f"{size_bytes / 1024:.2f} КБ"
        return f"{size_bytes} Б"

    def check_feed_freshness(self, feed_type: FeedType, parsed: ParsedFeed) -> Issue | None:
        """Проверяет возраст даты формирования фида товаров."""
        if feed_type != FeedType.PRODUCT or parsed.feed_date is None:
            return None

        age_minutes = (utc_now() - parsed.feed_date.astimezone(UTC)).total_seconds() / 60
        limit = self._settings.get_feed_age_limit_minutes(feed_type.value)
        if age_minutes <= limit:
            return None

        hours = int(age_minutes // 60)
        minutes = int(age_minutes % 60)
        age_label = f"{hours} ч {minutes} мин" if hours else f"{minutes} мин"
        return Issue(
            fingerprint=IssueRegistry.build_fingerprint(
                IssueCategory.STALE_DATA,
                feed_type,
                field="feed_date",
            ),
            severity=Severity.WARNING,
            category=IssueCategory.STALE_DATA,
            feed_type=feed_type,
            message_key="STALE_DATA",
            context={
                "object_type": "фид товаров",
                "feed_date": format_datetime_moscow(parsed.feed_date),
                "age": age_label,
            },
        )

    def check_outlet_freshness(
        self,
        feed_type: FeedType,
        store_id: str,
        store_name: str,
        actualization_datetime,
    ) -> Issue | None:
        """Проверяет актуальность actualization-date магазина."""
        if actualization_datetime is None:
            return Issue(
                fingerprint=IssueRegistry.build_fingerprint(
                    IssueCategory.INVALID_DATE,
                    feed_type,
                    object_id=store_id,
                    field="actualization-date",
                ),
                severity=Severity.WARNING,
                category=IssueCategory.INVALID_DATE,
                feed_type=feed_type,
                message_key="MISSING_REQUIRED_FIELD",
                object_id=store_id,
                object_name=store_name,
                context={"name": store_name, "field": "actualization-date"},
            )

        age_days = (utc_now() - actualization_datetime.astimezone(UTC)).days
        if age_days <= self._settings.max_outlet_age_days:
            return None

        return Issue(
            fingerprint=IssueRegistry.build_fingerprint(
                IssueCategory.STALE_DATA,
                feed_type,
                object_id=store_id,
                field="actualization-date",
            ),
            severity=Severity.WARNING,
            category=IssueCategory.STALE_DATA,
            feed_type=feed_type,
            message_key="STALE_DATA",
            object_id=store_id,
            object_name=store_name,
            context={
                "object_type": "магазин",
                "feed_date": format_datetime_moscow(actualization_datetime),
                "age": f"{age_days} дн.",
            },
        )
