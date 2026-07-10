"""Репозиторий очистки устаревших данных."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    ActiveErrorModel,
    AuthorizationLogModel,
    ErrorHistoryModel,
    FeedCheckModel,
    ProductPriceSnapshotModel,
)


@dataclass(slots=True)
class PurgeStats:
    """Статистика удаления устаревших записей."""

    authorization_log: int = 0
    feed_checks: int = 0
    error_history: int = 0
    active_errors: int = 0
    product_price_snapshots: int = 0

    @property
    def total(self) -> int:
        return (
            self.authorization_log
            + self.feed_checks
            + self.error_history
            + self.active_errors
            + self.product_price_snapshots
        )


class RetentionRepository:
    """Удаляет записи старше заданного срока хранения."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def purge_authorization_log(self, cutoff: datetime) -> int:
        """Удаляет записи журнала авторизации старше cutoff."""
        result = await self._session.execute(
            delete(AuthorizationLogModel).where(AuthorizationLogModel.created_at < cutoff)
        )
        return result.rowcount or 0

    async def purge_feed_checks(self, cutoff: datetime) -> int:
        """Удаляет историю проверок старше cutoff."""
        result = await self._session.execute(
            delete(FeedCheckModel).where(FeedCheckModel.started_at < cutoff)
        )
        return result.rowcount or 0

    async def purge_error_history(self, cutoff: datetime) -> int:
        """Удаляет историю ошибок старше cutoff."""
        result = await self._session.execute(
            delete(ErrorHistoryModel).where(ErrorHistoryModel.created_at < cutoff)
        )
        return result.rowcount or 0

    async def purge_stale_active_errors(self, cutoff: datetime) -> int:
        """
        Удаляет активные ошибки, не обновлявшиеся дольше срока хранения.

        Если проблема снова появится при проверке, она будет зарегистрирована заново.
        """
        result = await self._session.execute(
            delete(ActiveErrorModel).where(ActiveErrorModel.last_seen < cutoff)
        )
        return result.rowcount or 0

    async def purge_product_price_snapshots(self, cutoff: datetime) -> int:
        """Удаляет устаревшие снимки цен товаров."""
        result = await self._session.execute(
            delete(ProductPriceSnapshotModel).where(ProductPriceSnapshotModel.updated_at < cutoff)
        )
        return result.rowcount or 0

    async def purge_all(self, cutoff: datetime) -> PurgeStats:
        """Удаляет устаревшие данные из всех таблиц с историей."""
        stats = PurgeStats(
            authorization_log=await self.purge_authorization_log(cutoff),
            feed_checks=await self.purge_feed_checks(cutoff),
            error_history=await self.purge_error_history(cutoff),
            active_errors=await self.purge_stale_active_errors(cutoff),
            product_price_snapshots=await self.purge_product_price_snapshots(cutoff),
        )
        await self._session.flush()
        return stats

    async def count_records(self) -> dict[str, int]:
        """Возвращает количество записей в таблицах с историей."""
        tables = {
            "authorization_log": AuthorizationLogModel,
            "feed_checks": FeedCheckModel,
            "error_history": ErrorHistoryModel,
            "active_errors": ActiveErrorModel,
            "product_price_snapshots": ProductPriceSnapshotModel,
        }
        counts: dict[str, int] = {}
        for name, model in tables.items():
            result = await self._session.execute(select(func.count()).select_from(model))
            counts[name] = int(result.scalar_one())
        return counts
