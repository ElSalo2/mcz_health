"""Сущность проверки фида."""

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import CheckStatus, FeedType


@dataclass(slots=True)
class FeedCheck:
    """Результат одного запуска проверки."""

    id: int | None
    feed_type: FeedType
    status: CheckStatus
    started_at: datetime
    finished_at: datetime | None
    duration_seconds: float | None
    item_count: int | None
    sha256: str | None
    content_size: int | None
    feed_date: datetime | None
    critical_count: int
    warning_count: int
    triggered_by: str | None = None
