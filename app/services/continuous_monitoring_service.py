"""Непрерывный фоновый цикл мониторинга фидов."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import suppress
from typing import TYPE_CHECKING

from app.bot.formatters.check_formatter import format_check_cycle_completed
from app.core.config import Settings
from app.core.error_handler import handle_service_errors
from app.services.notification_service import NotificationService

if TYPE_CHECKING:
    from app.domain.value_objects.check_result import CheckResult
    from app.services.monitoring.orchestrator import CheckOrchestrator

logger = logging.getLogger(__name__)


class ContinuousMonitoringService:
    """
    Непрерывный фоновый мониторинг каталога.

    Цикл работы:
    1. Скачать фиды товаров и магазинов.
    2. Проверить все объекты из фидов (не более max_check_duration_seconds).
    3. При нарушениях — отправить алерты пользователям.
    4. По завершении или таймауту — сразу скачать новый фид и повторить цикл.
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
        self._active_cycle_task: asyncio.Task[list[CheckResult]] | None = None
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
        await self._abort_active_cycle()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("Фоновый мониторинг остановлен")

    async def _abort_active_cycle(
        self,
        cycle_task: asyncio.Task[list[CheckResult]] | None = None,
    ) -> None:
        """Прерывает текущий цикл проверки и закрывает незавершённые записи в БД."""
        task = cycle_task if cycle_task is not None else self._active_cycle_task
        self._orchestrator.request_abort()
        if task is not None and not task.done():
            task.cancel()
        if task is not None:
            with suppress(asyncio.CancelledError):
                await task
        self._active_cycle_task = None
        await self._orchestrator.fail_incomplete_checks()
        self._orchestrator.clear_abort()

    async def _run_loop(self) -> None:
        """Основной бесконечный цикл: скачать → проверить → повторить."""
        while not self._stop_event.is_set():
            try:
                completed_normally = await self._run_cycle()
            except Exception:
                logger.exception("Ошибка в цикле фонового мониторинга")
                completed_normally = False

            if not completed_normally and not self._stop_event.is_set():
                logger.info(
                    "Прерванный цикл завершён — сразу запускаем новый со свежими фидами"
                )

    @handle_service_errors
    async def _run_cycle(self) -> bool:
        """
        Выполняет один полный цикл проверки обоих фидов.

        Returns:
            True — цикл завершён штатно, False — прерван по таймауту или ошибке.
        """
        started = time.perf_counter()
        remaining = self._settings.max_check_duration_seconds
        cycle_task = asyncio.create_task(
            self._orchestrator.run_full_cycle(triggered_by="background"),
            name="monitoring-full-cycle",
        )
        self._active_cycle_task = cycle_task
        try:
            results = await asyncio.wait_for(cycle_task, timeout=remaining)
        except TimeoutError:
            logger.error(
                "Превышен лимит длительности проверки (%d мин)",
                self._settings.max_check_duration_seconds // 60,
            )
            await self._abort_active_cycle(cycle_task)
            return False
        except asyncio.CancelledError:
            await self._abort_active_cycle(cycle_task)
            raise
        finally:
            if self._active_cycle_task is cycle_task:
                self._active_cycle_task = None

        if results:
            checks = [result.feed_check for result in results]
            duration = time.perf_counter() - started
            summary = format_check_cycle_completed(checks, duration)
            logger.info("Цикл мониторинга завершён: %s", summary)
        return True
