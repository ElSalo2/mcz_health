"""Менеджер жизненного цикла базы данных."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.infrastructure.database.base import (
    create_engine,
    create_session_factory,
    init_database,
    vacuum_database,
    verify_database_connection,
)
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.services.retention_service import RetentionService

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Управляет подключением к БД и фабрикой сессий."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def startup(self) -> None:
        """Инициализирует движок, создаёт таблицы и проверяет соединение."""
        database_url = self._settings.get_resolved_database_url()
        self._settings.ensure_directories()

        self._engine = create_engine(database_url)
        self._session_factory = create_session_factory(self._engine)

        await init_database(self._engine)
        await verify_database_connection(self._engine)
        logger.info("Подключение к БД установлено: %s", database_url)

        await self._run_retention_cleanup()

    async def shutdown(self) -> None:
        """Закрывает соединение с базой данных."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Подключение к БД закрыто")

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("DatabaseManager не инициализирован")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("DatabaseManager не инициализирован")
        return self._session_factory

    async def _run_retention_cleanup(self) -> None:
        """Удаляет устаревшие данные при запуске приложения."""
        if self._engine is None or self._session_factory is None:
            return

        try:
            purge_total = 0
            async with UnitOfWork(self._session_factory) as uow:
                service = RetentionService(self._settings, uow, self._engine)
                result = await service.run_cleanup()
                purge_total = result.purge_stats.total

            if purge_total > 0:
                await vacuum_database(self._engine)
        except Exception:
            logger.exception("Ошибка при очистке устаревших данных")
