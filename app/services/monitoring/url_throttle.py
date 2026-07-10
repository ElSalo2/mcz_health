"""Расчёт интервала между HTTP-проверками URL."""

from __future__ import annotations

import logging

from app.core.config import Settings

logger = logging.getLogger(__name__)


class UrlThrottlePlanner:
    """
    Распределяет HTTP-проверки равномерно в отведённом бюджете времени.

    Бюджет = MAX_CHECK_DURATION_SECONDS − LOCAL_CHECK_RESERVE_SECONDS.
    Интервал на один URL = бюджет / количество URL.
  """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._slot_seconds: float | None = None

    @property
    def http_check_budget_seconds(self) -> float:
        """Время, выделенное на HTTP-проверки в одном цикле (секунды)."""
        return float(
            self._settings.max_check_duration_seconds
            - self._settings.local_check_reserve_seconds
        )

    @property
    def slot_seconds(self) -> float | None:
        """Текущий интервал между URL или None, если ещё не рассчитан."""
        return self._slot_seconds

    def plan_for_url_count(self, url_count: int) -> float:
        """
        Рассчитывает интервал между HTTP-запросами для заданного числа URL.

        Возвращает 0.0, если HTTP-проверки не требуются.
        """
        if url_count < 0:
            raise ValueError("Количество URL не может быть отрицательным")

        if url_count == 0:
            self._slot_seconds = 0.0
            logger.info("HTTP-проверки URL не требуются (0 URL)")
            return 0.0

        budget = self.http_check_budget_seconds
        if budget <= 0:
            raise ValueError(
                "Бюджет HTTP-проверок должен быть положительным. "
                "Увеличьте MAX_CHECK_DURATION_SECONDS или уменьшите "
                "LOCAL_CHECK_RESERVE_SECONDS."
            )

        slot = budget / url_count
        self._slot_seconds = slot
        logger.info(
            "HTTP-троттлинг: %s URL, бюджет %.0f с, интервал %.3f с/URL",
            url_count,
            budget,
            slot,
        )
        return slot

    def seconds_until_next_request(self, elapsed_seconds: float) -> float:
        """Возвращает паузу до следующего URL с учётом уже потраченного времени."""
        if self._slot_seconds is None or self._slot_seconds <= 0:
            return 0.0
        return max(0.0, self._slot_seconds - elapsed_seconds)
