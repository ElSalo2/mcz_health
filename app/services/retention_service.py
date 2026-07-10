"""Сервис контроля объёма данных и срока хранения."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.core.error_handler import handle_service_errors
from app.infrastructure.database.repositories.retention_repository import PurgeStats, RetentionRepository
from app.infrastructure.database.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CleanupResult:
    """Результат очистки данных."""

    purge_stats: PurgeStats
    removed_log_files: int
    database_size_mb: float
    cutoff: datetime


class RetentionService:
    """Управляет сроком хранения данных в БД и файловых логах."""

    def __init__(
        self,
        settings: Settings,
        unit_of_work: UnitOfWork,
        engine: AsyncEngine,
    ) -> None:
        self._settings = settings
        self._uow = unit_of_work
        self._engine = engine

    def get_cutoff_datetime(self) -> datetime:
        """Возвращает границу хранения: записи старше этой даты удаляются."""
        return datetime.now(UTC) - timedelta(days=self._settings.data_retention_days)

    @handle_service_errors
    async def run_cleanup(self) -> CleanupResult:
        """Удаляет устаревшие данные из БД, логов и освобождает место."""
        cutoff = self.get_cutoff_datetime()
        repository = RetentionRepository(self._uow.session)

        logger.info(
            "Запуск очистки данных старше %s дней (до %s)",
            self._settings.data_retention_days,
            cutoff.isoformat(),
        )

        purge_stats = await repository.purge_all(cutoff)
        removed_log_files = self.cleanup_log_files()

        db_size = self.get_database_size_mb()
        result = CleanupResult(
            purge_stats=purge_stats,
            removed_log_files=removed_log_files,
            database_size_mb=db_size,
            cutoff=cutoff,
        )

        logger.info(
            "Очистка завершена: удалено записей=%d (auth=%d, checks=%d, errors=%d, active=%d), "
            "файлов логов=%d, размер БД=%.2f МБ",
            purge_stats.total,
            purge_stats.authorization_log,
            purge_stats.feed_checks,
            purge_stats.error_history,
            purge_stats.active_errors,
            removed_log_files,
            db_size,
        )
        return result

    def cleanup_log_files(self, logs_dir: Path | None = None) -> int:
        """Удаляет файлы логов старше срока хранения."""
        target_dir = logs_dir or self._settings.logs_dir
        if not target_dir.exists():
            return 0

        cutoff_timestamp = (
            datetime.now(UTC) - timedelta(days=self._settings.log_retention_days)
        ).timestamp()
        removed = 0

        for log_file in target_dir.glob("catalog_monitor.log*"):
            if not log_file.is_file():
                continue
            if log_file.stat().st_mtime < cutoff_timestamp:
                log_file.unlink(missing_ok=True)
                removed += 1
                logger.debug("Удалён устаревший лог: %s", log_file.name)

        return removed

    def get_database_size_mb(self) -> float:
        """Возвращает текущий размер файла SQLite в мегабайтах."""
        db_path = self._settings.get_sqlite_path()
        if db_path is None or not db_path.exists():
            return 0.0
        return db_path.stat().st_size / (1024 * 1024)
