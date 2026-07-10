"""Репозиторий проверок фидов."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseError
from app.domain.entities.feed_check import FeedCheck
from app.domain.enums import CheckStatus, FeedType
from app.infrastructure.database.models import FeedCheckModel


class CheckRepository:
    """Доступ к данным проверок."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, feed_check: FeedCheck) -> FeedCheck:
        """Создаёт запись о проверке."""
        model = FeedCheckModel(
            feed_type=feed_check.feed_type.value,
            status=feed_check.status.value,
            started_at=feed_check.started_at,
            finished_at=feed_check.finished_at,
            duration_seconds=feed_check.duration_seconds,
            item_count=feed_check.item_count,
            sha256=feed_check.sha256,
            content_size=feed_check.content_size,
            feed_date=feed_check.feed_date,
            critical_count=feed_check.critical_count,
            warning_count=feed_check.warning_count,
            triggered_by=feed_check.triggered_by,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def update(self, feed_check: FeedCheck) -> FeedCheck:
        """Обновляет запись о проверке."""
        if feed_check.id is None:
            raise DatabaseError("Невозможно обновить проверку без ID")

        result = await self._session.execute(
            select(FeedCheckModel).where(FeedCheckModel.id == feed_check.id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise DatabaseError("Проверка не найдена", details={"id": feed_check.id})

        model.status = feed_check.status.value
        model.finished_at = feed_check.finished_at
        model.duration_seconds = feed_check.duration_seconds
        model.item_count = feed_check.item_count
        model.sha256 = feed_check.sha256
        model.content_size = feed_check.content_size
        model.feed_date = feed_check.feed_date
        model.critical_count = feed_check.critical_count
        model.warning_count = feed_check.warning_count
        model.triggered_by = feed_check.triggered_by

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, check_id: int) -> FeedCheck | None:
        """Возвращает проверку по ID."""
        result = await self._session.execute(
            select(FeedCheckModel).where(FeedCheckModel.id == check_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_last_successful(self, feed_type: FeedType) -> FeedCheck | None:
        """Возвращает последнюю успешную проверку."""
        result = await self._session.execute(
            select(FeedCheckModel)
            .where(
                FeedCheckModel.feed_type == feed_type.value,
                FeedCheckModel.status == CheckStatus.SUCCESS.value,
            )
            .order_by(desc(FeedCheckModel.finished_at), desc(FeedCheckModel.started_at))
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_running(self) -> list[FeedCheck]:
        """Возвращает незавершённые проверки."""
        result = await self._session.execute(
            select(FeedCheckModel).where(FeedCheckModel.status == CheckStatus.RUNNING.value)
        )
        return [self._to_entity(model) for model in result.scalars().all()]

    async def get_last(self, feed_type: FeedType | None = None) -> FeedCheck | None:
        """Возвращает последнюю проверку."""
        query = select(FeedCheckModel).order_by(
            desc(FeedCheckModel.started_at),
            desc(FeedCheckModel.id),
        )
        if feed_type is not None:
            query = query.where(FeedCheckModel.feed_type == feed_type.value)
        query = query.limit(1)

        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_history(
        self,
        feed_type: FeedType | None = None,
        limit: int = 10,
    ) -> list[FeedCheck]:
        """Возвращает историю проверок."""
        query = select(FeedCheckModel).order_by(
            desc(FeedCheckModel.started_at),
            desc(FeedCheckModel.id),
        )
        if feed_type is not None:
            query = query.where(FeedCheckModel.feed_type == feed_type.value)
        query = query.limit(limit)

        result = await self._session.execute(query)
        return [self._to_entity(model) for model in result.scalars().all()]

    @staticmethod
    def _to_entity(model: FeedCheckModel) -> FeedCheck:
        return FeedCheck(
            id=model.id,
            feed_type=FeedType(model.feed_type),
            status=CheckStatus(model.status),
            started_at=model.started_at,
            finished_at=model.finished_at,
            duration_seconds=model.duration_seconds,
            item_count=model.item_count,
            sha256=model.sha256,
            content_size=model.content_size,
            feed_date=model.feed_date,
            critical_count=model.critical_count,
            warning_count=model.warning_count,
            triggered_by=model.triggered_by,
        )
