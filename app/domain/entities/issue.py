"""Сущность обнаруженной проблемы."""

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.enums import FeedType, IssueCategory, Severity


@dataclass(slots=True)
class Issue:
    """Проблема, обнаруженная при проверке каталога."""

    fingerprint: str
    severity: Severity
    category: IssueCategory
    feed_type: FeedType
    message_key: str
    context: dict[str, object] = field(default_factory=dict)
    object_id: str | None = None
    object_name: str | None = None

    def __hash__(self) -> int:
        return hash(self.fingerprint)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Issue):
            return NotImplemented
        return self.fingerprint == other.fingerprint


@dataclass(slots=True)
class ActiveError:
    """Активная (неустранённая) ошибка в системе."""

    id: int | None
    fingerprint: str
    severity: Severity
    category: IssueCategory
    feed_type: FeedType
    context_json: dict[str, object]
    first_seen: datetime
    last_seen: datetime
    notified: bool
