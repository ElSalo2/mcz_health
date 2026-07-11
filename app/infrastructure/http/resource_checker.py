"""Проверка доступности URL и изображений."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

from app.infrastructure.http.client import HttpClient, HttpResponse
from app.services.monitoring.check_stats_tracker import CheckStatsTracker
from app.services.monitoring.url_throttle import UrlThrottlePlanner

logger = logging.getLogger(__name__)


class ResourceChecker:
    """
    Проверяет доступность ресурсов последовательно с равномерным интервалом.

    Интервал задаётся через UrlThrottlePlanner и рассчитывается как
    (бюджет HTTP-проверок) / (количество URL), чтобы не перегружать сайт.
    """

    def __init__(self, http_client: HttpClient, throttle_planner: UrlThrottlePlanner) -> None:
        self._http_client = http_client
        self._throttle = throttle_planner
        self._stats_tracker: CheckStatsTracker | None = None
        self._abort_check: Callable[[], bool] | None = None

    def set_stats_tracker(self, tracker: CheckStatsTracker | None) -> None:
        """Подключает сбор статистики HTTP-проверок."""
        self._stats_tracker = tracker

    def set_abort_check(self, check: Callable[[], bool] | None) -> None:
        """Подключает проверку запроса на прерывание HTTP-обхода."""
        self._abort_check = check

    def _ensure_not_aborted(self) -> None:
        if self._abort_check is not None and self._abort_check():
            raise asyncio.CancelledError("HTTP-проверки прерваны")

    async def check_url(self, url: str, *, kind: str = "unknown") -> HttpResponse:
        """Проверяет URL: сначала HEAD, при неудаче — GET с Range."""
        self._ensure_not_aborted()
        started = time.perf_counter()
        try:
            response = await self._http_client.head(url)
            if response.status_code is not None and response.status_code < 400:
                pass
            else:
                response = await self._http_client.get_range(url)
        except Exception as exc:
            logger.debug("Ошибка проверки URL %s: %s", url, exc)
            response = HttpResponse(
                url=url,
                status_code=None,
                content_type=None,
                content_length=None,
                error=str(exc),
            )

        if self._stats_tracker is not None and kind != "unknown":
            self._stats_tracker.record_http(response, kind=kind)
            await self._stats_tracker.maybe_flush()

        await self._wait_slot(started)
        self._ensure_not_aborted()
        return response

    async def check_urls(self, urls: list[str]) -> list[HttpResponse]:
        """Проверяет список URL последовательно с рассчитанным интервалом."""
        if not urls:
            return []

        if self._throttle.slot_seconds is None:
            self._throttle.plan_for_url_count(len(urls))
        results: list[HttpResponse] = []
        for url in urls:
            self._ensure_not_aborted()
            results.append(await self.check_url(url))
        return results

    async def _wait_slot(self, started: float) -> None:
        if self._throttle.slot_seconds is None or self._throttle.slot_seconds <= 0:
            return
        delay = self._throttle.seconds_until_next_request(time.perf_counter() - started)
        if delay > 0:
            await asyncio.sleep(delay)
