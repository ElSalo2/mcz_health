"""Сбор и сохранение статистики проверки в реальном времени."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.entities.feed_check import FeedCheck
from app.domain.enums import FeedType
from app.domain.value_objects.check_stats import CheckStats
from app.infrastructure.database.unit_of_work import UnitOfWork

if TYPE_CHECKING:
    from app.infrastructure.http.client import HttpResponse

logger = logging.getLogger(__name__)

HTTP_KIND_FIELDS = {
    "product_page": ("product_pages_checked", "product_pages_ok"),
    "product_image": ("product_images_checked", "product_images_ok"),
    "store_page": ("store_pages_checked", "store_pages_ok"),
    "store_image": ("store_images_checked", "store_images_ok"),
}

FLUSH_EVERY_HTTP = 100
FLUSH_INTERVAL_SECONDS = 30.0


class CheckStatsTracker:
    """Накапливает статистику проверки и периодически сохраняет её в БД."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory
        self._check_ids: dict[FeedType, int] = {}
        self._stats: dict[FeedType, CheckStats] = {}
        self._http_since_flush = 0
        self._last_flush_at = time.monotonic()
        self._flush_lock = asyncio.Lock()

    def bind_check(self, feed_type: FeedType, check_id: int, stats: CheckStats) -> None:
        """Привязывает трекер к записи проверки в БД."""
        self._check_ids[feed_type] = check_id
        self._stats[feed_type] = stats

    def get_stats(self, feed_type: FeedType) -> CheckStats | None:
        return self._stats.get(feed_type)

    def record_http(self, response: HttpResponse, *, kind: str) -> None:
        """Учитывает результат HTTP-проверки."""
        fields = HTTP_KIND_FIELDS.get(kind)
        if fields is None:
            return

        feed_type = FeedType.PRODUCT if kind.startswith("product_") else FeedType.STORE
        stats = self._stats.get(feed_type)
        if stats is None:
            return

        checked_field, ok_field = fields
        setattr(stats, checked_field, getattr(stats, checked_field) + 1)
        stats.http_total_checked += 1
        if response.status_code is not None and response.status_code < 400:
            setattr(stats, ok_field, getattr(stats, ok_field) + 1)
            stats.http_total_ok += 1

        self._http_since_flush += 1

    def increment(self, feed_type: FeedType, field: str, amount: int = 1) -> None:
        stats = self._stats.get(feed_type)
        if stats is None or not hasattr(stats, field):
            return
        setattr(stats, field, getattr(stats, field) + amount)

    async def maybe_flush(self) -> None:
        """Сохраняет статистику в БД при достижении порога."""
        if self._http_since_flush < FLUSH_EVERY_HTTP and (
            time.monotonic() - self._last_flush_at
        ) < FLUSH_INTERVAL_SECONDS:
            return
        await self.flush()

    async def flush(self) -> None:
        """Сохраняет текущую статистику всех активных проверок."""
        async with self._flush_lock:
            if not self._check_ids:
                return
            async with UnitOfWork(self._session_factory) as uow:
                for feed_type, check_id in self._check_ids.items():
                    stats = self._stats.get(feed_type)
                    if stats is None:
                        continue
                    check = await uow.checks.get_by_id(check_id)
                    if check is None:
                        continue
                    await uow.checks.update_stats(check_id, stats.to_dict())
            self._http_since_flush = 0
            self._last_flush_at = time.monotonic()
