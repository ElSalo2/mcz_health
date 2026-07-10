"""Результат проверки."""

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.entities.feed_check import FeedCheck
from app.domain.entities.issue import Issue
from app.domain.enums import FeedType


@dataclass(slots=True)
class CheckResult:
    """Итог выполнения полного цикла проверки."""

    feed_type: FeedType
    feed_check: FeedCheck
    issues: list[Issue] = field(default_factory=list)
    new_issues: list[Issue] = field(default_factory=list)
    resolved_issues: list[Issue] = field(default_factory=list)
    skipped: bool = False
    finished_at: datetime | None = None

    @property
    def critical_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity.value == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity.value == "warning")
