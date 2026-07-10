"""Репозиторий ошибок."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.issue import ActiveError, Issue
from app.domain.enums import ErrorEventType, FeedType, IssueCategory, Severity
from app.infrastructure.database.models import ActiveErrorModel, ErrorHistoryModel
from app.infrastructure.database.utils import dump_json, load_json, utc_now


class ErrorRepository:
    """Доступ к данным об ошибках."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_errors(self, feed_type: FeedType | None = None) -> list[ActiveError]:
        """Возвращает список активных ошибок."""
        query = select(ActiveErrorModel).order_by(ActiveErrorModel.first_seen.desc())
        if feed_type is not None:
            query = query.where(ActiveErrorModel.feed_type == feed_type.value)

        result = await self._session.execute(query)
        return [self._to_active_error(model) for model in result.scalars().all()]

    async def get_active_by_fingerprint(self, fingerprint: str) -> ActiveError | None:
        """Возвращает активную ошибку по отпечатку."""
        result = await self._session.execute(
            select(ActiveErrorModel).where(ActiveErrorModel.fingerprint == fingerprint)
        )
        model = result.scalar_one_or_none()
        return self._to_active_error(model) if model else None

    async def upsert_active_error(self, issue: Issue, *, notified: bool = False) -> ActiveError:
        """Создаёт или обновляет активную ошибку."""
        now = utc_now()
        result = await self._session.execute(
            select(ActiveErrorModel).where(ActiveErrorModel.fingerprint == issue.fingerprint)
        )
        model = result.scalar_one_or_none()

        if model is None:
            context = dict(issue.context)
            context["message_key"] = issue.message_key
            model = ActiveErrorModel(
                fingerprint=issue.fingerprint,
                severity=issue.severity.value,
                category=issue.category.value,
                feed_type=issue.feed_type.value,
                context_json=dump_json(context),
                first_seen=now,
                last_seen=now,
                notified=notified,
            )
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model)
            return self._to_active_error(model)

        model.severity = issue.severity.value
        model.category = issue.category.value
        model.feed_type = issue.feed_type.value
        context = dict(issue.context)
        context["message_key"] = issue.message_key
        model.context_json = dump_json(context)
        model.last_seen = now
        if notified:
            model.notified = True

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_active_error(model)

    async def mark_notified(self, fingerprint: str) -> None:
        """Помечает ошибку как уведомлённую."""
        result = await self._session.execute(
            select(ActiveErrorModel).where(ActiveErrorModel.fingerprint == fingerprint)
        )
        model = result.scalar_one_or_none()
        if model is not None:
            model.notified = True

    async def resolve_error(self, fingerprint: str, context: dict | None = None) -> None:
        """Удаляет активную ошибку и записывает событие устранения."""
        await self._session.execute(
            delete(ActiveErrorModel).where(ActiveErrorModel.fingerprint == fingerprint)
        )
        await self._session.flush()
        await self.add_history_event(
            fingerprint=fingerprint,
            event_type=ErrorEventType.RESOLVED,
            context=context or {},
        )

    async def add_history_event(
        self,
        fingerprint: str,
        event_type: ErrorEventType,
        context: dict,
    ) -> None:
        """Добавляет событие в историю ошибок."""
        history_entry = ErrorHistoryModel(
            fingerprint=fingerprint,
            event_type=event_type.value,
            context_json=dump_json(context),
        )
        self._session.add(history_entry)
        await self._session.flush()

    async def list_history(
        self,
        fingerprint: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Возвращает историю событий ошибок."""
        query = select(ErrorHistoryModel).order_by(ErrorHistoryModel.created_at.desc())
        if fingerprint is not None:
            query = query.where(ErrorHistoryModel.fingerprint == fingerprint)
        query = query.limit(limit)

        result = await self._session.execute(query)
        return [
            {
                "id": row.id,
                "fingerprint": row.fingerprint,
                "event_type": row.event_type,
                "context": load_json(row.context_json),
                "created_at": row.created_at,
            }
            for row in result.scalars().all()
        ]

    @staticmethod
    def _to_active_error(model: ActiveErrorModel) -> ActiveError:
        return ActiveError(
            id=model.id,
            fingerprint=model.fingerprint,
            severity=Severity(model.severity),
            category=IssueCategory(model.category),
            feed_type=FeedType(model.feed_type),
            context_json=load_json(model.context_json),
            first_seen=model.first_seen,
            last_seen=model.last_seen,
            notified=model.notified,
        )
