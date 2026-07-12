"""Расчёт интервала между HTTP-проверками URL."""

from __future__ import annotations

import logging

from app.core.config import Settings

logger = logging.getLogger(__name__)


class UrlThrottlePlanner:
    """
    Задаёт фиксированную паузу между HTTP-запросами.

    Интервал настраивается через HTTP_URL_SLOT_SECONDS и не зависит
    от MAX_CHECK_DURATION_SECONDS (это только потолок цикла).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._slot_seconds: float | None = None

    @property
    def slot_seconds(self) -> float | None:
        """Текущий интервал между URL или None, если ещё не рассчитан."""
        return self._slot_seconds

    def plan_for_url_count(self, url_count: int) -> float:
        """
        Возвращает интервал между HTTP-запросами для цикла.

        Количество URL используется только для оценки длительности и предупреждений.
        """
        if url_count < 0:
            raise ValueError("Количество URL не может быть отрицательным")

        if url_count == 0:
            self._slot_seconds = 0.0
            logger.info("HTTP-проверки URL не требуются (0 URL)")
            return 0.0

        slot = self._settings.http_url_slot_seconds_value
        self._slot_seconds = slot
        estimated_http = self._settings.estimate_http_phase_seconds(url_count)
        estimated_total = estimated_http + self._settings.local_check_reserve_seconds
        if estimated_total > self._settings.max_check_duration_seconds:
            logger.warning(
                "Оценка длительности цикла %.0f с превышает лимит %s с "
                "(HTTP %.0f с + локальные %s с). "
                "Увеличьте MAX_CHECK_DURATION_SECONDS или уменьшите HTTP_URL_SLOT_SECONDS.",
                estimated_total,
                self._settings.max_check_duration_seconds,
                estimated_http,
                self._settings.local_check_reserve_seconds,
            )

        logger.info(
            "HTTP-троттлинг: %s URL, интервал %.3f с/URL, оценка HTTP-этапа %.0f с",
            url_count,
            slot,
            estimated_http,
        )
        return slot

    def seconds_until_next_request(self, elapsed_seconds: float) -> float:
        """Возвращает паузу до следующего URL с учётом уже потраченного времени."""
        if self._slot_seconds is None or self._slot_seconds <= 0:
            return 0.0
        return max(0.0, self._slot_seconds - elapsed_seconds)
