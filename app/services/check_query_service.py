"""Сервис получения данных о проверках для Telegram."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.formatters.check_formatter import format_history_report, format_last_check_report
from app.core.error_handler import handle_service_errors
from app.domain.entities.feed_check import FeedCheck
from app.domain.enums import FeedType
from app.domain.value_objects.feed_check_view import FeedCheckView
from app.infrastructure.database.unit_of_work import UnitOfWork


class CheckQueryService:
    """Чтение и форматирование результатов проверок."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _build_feed_view(running: list[FeedCheck], completed: FeedCheck | None) -> FeedCheckView:
        if running:
            current = running[0]
            previous = completed if completed is None or completed.id != current.id else None
            return FeedCheckView(current=current, previous=previous)
        return FeedCheckView(current=completed, previous=None)

    @handle_service_errors
    async def get_feed_check_view(self, feed_type: FeedType) -> FeedCheckView:
        """Возвращает текущую и предыдущую проверку для типа фида."""
        async with UnitOfWork(self._session_factory) as uow:
            running = await uow.checks.list_running(feed_type)
            completed = await uow.checks.get_last_completed(feed_type)
        return self._build_feed_view(running, completed)

    @handle_service_errors
    async def get_last_check_report(self) -> str:
        """Возвращает текстовый отчёт о последних проверках."""
        async with UnitOfWork(self._session_factory) as uow:
            store_running = await uow.checks.list_running(FeedType.STORE)
            store_completed = await uow.checks.get_last_completed(FeedType.STORE)
            product_running = await uow.checks.list_running(FeedType.PRODUCT)
            product_completed = await uow.checks.get_last_completed(FeedType.PRODUCT)

        store_view = self._build_feed_view(store_running, store_completed)
        product_view = self._build_feed_view(product_running, product_completed)
        return format_last_check_report(product_view, store_view)

    @handle_service_errors
    async def get_history_report(self, limit: int = 10) -> str:
        """Возвращает текстовую историю проверок."""
        async with UnitOfWork(self._session_factory) as uow:
            checks = await uow.checks.list_history(feed_type=None, limit=limit)
        return format_history_report(checks)

    @handle_service_errors
    async def get_last_checks(self) -> tuple[FeedCheck | None, FeedCheck | None]:
        """Возвращает последние проверки товаров и магазинов."""
        product_view = await self.get_feed_check_view(FeedType.PRODUCT)
        store_view = await self.get_feed_check_view(FeedType.STORE)
        return product_view.current, store_view.current
