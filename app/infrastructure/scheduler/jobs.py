"""Задачи APScheduler."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import Settings
from app.infrastructure.database.base import vacuum_database
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.services.retention_service import RetentionService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


def create_scheduler() -> AsyncIOScheduler:
    """Создаёт экземпляр планировщика."""
    return AsyncIOScheduler(timezone="Europe/Moscow")


async def _run_retention_job(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    engine: AsyncEngine,
) -> None:
    """Периодическая очистка устаревших данных."""
    try:
        purge_total = 0
        async with UnitOfWork(session_factory) as uow:
            service = RetentionService(settings, uow, engine)
            result = await service.run_cleanup()
            purge_total = result.purge_stats.total

        if purge_total > 0:
            await vacuum_database(engine)
    except Exception:
        logger.exception("Ошибка при плановой очистке данных")


def register_retention_job(
    scheduler: AsyncIOScheduler,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    engine: AsyncEngine,
) -> None:
    """Регистрирует задачу периодической очистки БД и логов."""
    scheduler.add_job(
        _run_retention_job,
        trigger="interval",
        seconds=settings.db_cleanup_interval,
        id="retention_cleanup",
        name="Очистка устаревших данных",
        replace_existing=True,
        kwargs={
            "settings": settings,
            "session_factory": session_factory,
            "engine": engine,
        },
    )
    logger.info(
        "Задача очистки данных зарегистрирована: каждые %d сек, хранение %d дней",
        settings.db_cleanup_interval,
        settings.data_retention_days,
    )


def register_jobs(scheduler: AsyncIOScheduler, settings: Settings, orchestrator) -> None:
    """
    Резерв для дополнительных периодических задач.

    Основной мониторинг фидов выполняется ContinuousMonitoringService
    в бесконечном фоновом цикле, а не по расписанию APScheduler.
    """
    logger.info(
        "Фоновый мониторинг: интервал скачивания %d сек, лимит проверки %d сек",
        settings.feed_download_interval,
        settings.max_check_duration_seconds,
    )
