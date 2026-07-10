"""Метаданные XML-фида."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FeedMetadata:
    """Метаданные, извлечённые из XML-фида."""

    feed_type: str
    feed_date: datetime | None
    raw_date: str | None
    item_count: int
    sha256: str
    size_bytes: int
