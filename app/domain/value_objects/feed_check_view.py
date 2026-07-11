"""Представление текущей и предыдущей проверки фида."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.feed_check import FeedCheck


@dataclass(slots=True)
class FeedCheckView:
    """Текущая (или последняя) и предыдущая завершённая проверка."""

    current: FeedCheck | None
    previous: FeedCheck | None = None
