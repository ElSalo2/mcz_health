"""Сервис получения данных о проверках для Telegram."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.formatters.check_formatter import format_history_report, format_last_check_report
from app.core.error_handler import handle_service_errors
from app.domain.entities.feed_check import FeedCheck
from app.domain.enums import FeedType
from app.infrastructure.database.unit_of_work import UnitOfWork


class CheckQueryService:
    """Чтение и форматирование результатов проверок."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @handle_service_errors
    async def get_last_check_report(self) -> str:
        """Возвращает текстовый отчёт о последних проверках."""
        async with UnitOfWork(self._session_factory) as uow:
            product_check = await uow.checks.get_last(FeedType.PRODUCT)
            store_check = await uow.checks.get_last(FeedType.STORE)
        return format_last_check_report(product_check, store_check)

    @handle_service_errors
    async def get_history_report(self, limit: int = 10) -> str:
        """Возвращает текстовую историю проверок."""
        async with UnitOfWork(self._session_factory) as uow:
            checks = await uow.checks.list_history(feed_type=None, limit=limit)
        return format_history_report(checks)

    @handle_service_errors
    async def get_last_checks(self) -> tuple[FeedCheck | None, FeedCheck | None]:
        """Возвращает последние проверки товаров и магазинов."""
        async with UnitOfWork(self._session_factory) as uow:
            product_check = await uow.checks.get_last(FeedType.PRODUCT)
            store_check = await uow.checks.get_last(FeedType.STORE)
        return product_check, store_check
