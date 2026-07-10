"""Проверка доступности URL и изображений."""

from __future__ import annotations

import asyncio
import logging
import time

from app.infrastructure.http.client import HttpClient, HttpResponse
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

    async def check_url(self, url: str) -> HttpResponse:
        """Проверяет URL: сначала HEAD, при неудаче — GET с Range."""
        started = time.perf_counter()
        try:
            response = await self._http_client.head(url)
            if response.status_code is not None and response.status_code < 400:
                return response
            return await self._http_client.get_range(url)
        except Exception as exc:
            logger.debug("Ошибка проверки URL %s: %s", url, exc)
            return HttpResponse(
                url=url,
                status_code=None,
                content_type=None,
                content_length=None,
                error=str(exc),
            )
        finally:
            await self._wait_slot(started)

    async def check_urls(self, urls: list[str]) -> list[HttpResponse]:
        """Проверяет список URL последовательно с рассчитанным интервалом."""
        if not urls:
            return []

        if self._throttle.slot_seconds is None:
            self._throttle.plan_for_url_count(len(urls))
        results: list[HttpResponse] = []
        for url in urls:
            results.append(await self.check_url(url))
        return results

    async def _wait_slot(self, started: float) -> None:
        if self._throttle.slot_seconds is None or self._throttle.slot_seconds <= 0:
            return
        delay = self._throttle.seconds_until_next_request(time.perf_counter() - started)
        if delay > 0:
            await asyncio.sleep(delay)
