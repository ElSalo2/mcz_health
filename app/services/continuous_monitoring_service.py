"""Непрерывный фоновый цикл мониторинга фидов."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from app.bot.formatters.check_formatter import format_check_cycle_completed
from app.core.config import Settings
from app.core.error_handler import handle_service_errors
from app.services.notification_service import NotificationService

if TYPE_CHECKING:
    from app.services.monitoring.orchestrator import CheckOrchestrator

logger = logging.getLogger(__name__)


class ContinuousMonitoringService:
    """
    Непрерывный фоновый мониторинг каталога.

    Цикл работы:
    1. Скачать фиды товаров и магазинов.
    2. Проверить все объекты из фидов (не более max_check_duration_seconds).
    3. При нарушениях — отправить алерты пользователям.
    4. По завершении — скачать новый фид и повторить цикл.
    5. Минимальный интервал между скачиваниями — feed_download_interval (3 ч).
    """

    def __init__(
        self,
        settings: Settings,
        orchestrator: CheckOrchestrator,
        notification_service: NotificationService,
    ) -> None:
        self._settings = settings
        self._orchestrator = orchestrator
        self._notification_service = notification_service
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        """Запускает фоновый цикл мониторинга."""
        if self.is_running:
            logger.warning("Фоновый мониторинг уже запущен")
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Запущен непрерывный фоновый мониторинг")

    async def stop(self) -> None:
        """Останавливает фоновый цикл мониторинга."""
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Фоновый мониторинг остановлен")

    async def _run_loop(self) -> None:
        """Основной бесконечный цикл: скачать → проверить → скачать."""
        while not self._stop_event.is_set():
            cycle_started = time.perf_counter()
            try:
                await self._run_cycle()
            except Exception:
                logger.exception("Ошибка в цикле фонового мониторинга")

            elapsed = time.perf_counter() - cycle_started
            wait_seconds = max(0.0, self._settings.feed_download_interval - elapsed)
            if wait_seconds > 0 and not self._stop_event.is_set():
                logger.info(
                    "Ожидание %.0f сек до следующего скачивания фида",
                    wait_seconds,
                )
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=wait_seconds)
                except TimeoutError:
                    pass

    @handle_service_errors
    async def _run_cycle(self) -> None:
        """Выполняет один полный цикл проверки обоих фидов."""
        started = time.perf_counter()
        remaining = self._settings.max_check_duration_seconds
        try:
            results = await asyncio.wait_for(
                self._orchestrator.run_full_cycle(triggered_by="background"),
                timeout=remaining,
            )
        except TimeoutError:
            logger.error("Превышен лимит длительности проверки (2 ч 59 мин)")
            await self._orchestrator.fail_incomplete_checks()
            return

        if results:
            checks = [result.feed_check for result in results]
            duration = time.perf_counter() - started
            summary = format_check_cycle_completed(checks, duration)
            logger.info("Цикл мониторинга завершён: %s", summary)
