"""Тесты непрерывного фонового мониторинга."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.domain.entities.feed_check import FeedCheck
from app.domain.enums import CheckStatus, FeedType
from app.domain.value_objects.check_result import CheckResult
from app.services.continuous_monitoring_service import ContinuousMonitoringService


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("BOT_TOKEN", "1234567890:ABCDEFghijklmnopQRSTUVwxyz")
    monkeypatch.setenv("ADMIN_ID", "1")
    monkeypatch.setenv(
        "STORE_FEED_URL",
        "https://st.sunlight.net/media/feed/outlets/yandex_outlets_mcz.xml",
    )
    monkeypatch.setenv(
        "PRODUCT_FEED_URL",
        "https://st.sunlight.net/media/feed/anyquery_mcz.xml",
    )
    return Settings()


@pytest.mark.asyncio
async def test_run_cycle_timeout_aborts_and_returns_false(settings: Settings) -> None:
    async def slow_cycle(**_: object) -> list[CheckResult]:
        await asyncio.sleep(3600)
        return []

    orchestrator = MagicMock()
    orchestrator.run_full_cycle = slow_cycle
    orchestrator.request_abort = MagicMock()
    orchestrator.clear_abort = MagicMock()
    orchestrator.fail_incomplete_checks = AsyncMock()

    service = ContinuousMonitoringService(settings, orchestrator, MagicMock())
    settings.max_check_duration_seconds = 0.05

    completed = await service._run_cycle()

    assert completed is False
    orchestrator.request_abort.assert_called_once()
    orchestrator.fail_incomplete_checks.assert_called_once()
    orchestrator.clear_abort.assert_called_once()


@pytest.mark.asyncio
async def test_run_cycle_success_returns_true(settings: Settings) -> None:
    feed_check = FeedCheck(
        id=1,
        feed_type=FeedType.PRODUCT,
        status=CheckStatus.SUCCESS,
        started_at=None,
        finished_at=None,
        duration_seconds=1.0,
        item_count=10,
        sha256=None,
        content_size=None,
        feed_date=None,
        critical_count=0,
        warning_count=0,
        triggered_by="background",
    )
    result = CheckResult(
        feed_type=FeedType.PRODUCT,
        feed_check=feed_check,
        issues=[],
        new_issues=[],
        resolved_issues=[],
        skipped=False,
        finished_at=None,
    )

    async def successful_cycle(**_: object) -> list[CheckResult]:
        return [result]

    orchestrator = MagicMock()
    orchestrator.run_full_cycle = successful_cycle
    orchestrator.request_abort = MagicMock()
    orchestrator.clear_abort = MagicMock()
    orchestrator.fail_incomplete_checks = AsyncMock()

    service = ContinuousMonitoringService(settings, orchestrator, MagicMock())

    completed = await service._run_cycle()

    assert completed is True
    orchestrator.fail_incomplete_checks.assert_not_called()


@pytest.mark.asyncio
async def test_completed_cycle_starts_immediately(settings: Settings) -> None:
    calls = 0

    async def cycle_behavior(**_: object) -> list[CheckResult]:
        nonlocal calls
        calls += 1
        feed_check = FeedCheck(
            id=calls,
            feed_type=FeedType.PRODUCT,
            status=CheckStatus.SUCCESS,
            started_at=None,
            finished_at=None,
            duration_seconds=1.0,
            item_count=10,
            sha256=None,
            content_size=None,
            feed_date=None,
            critical_count=0,
            warning_count=0,
            triggered_by="background",
        )
        return [
            CheckResult(
                feed_type=FeedType.PRODUCT,
                feed_check=feed_check,
                issues=[],
                new_issues=[],
                resolved_issues=[],
                skipped=False,
                finished_at=None,
            )
        ]

    orchestrator = MagicMock()
    orchestrator.run_full_cycle = cycle_behavior
    orchestrator.request_abort = MagicMock()
    orchestrator.clear_abort = MagicMock()
    orchestrator.fail_incomplete_checks = AsyncMock()

    service = ContinuousMonitoringService(settings, orchestrator, MagicMock())
    settings.feed_download_interval = 10_000

    service.start()
    await asyncio.sleep(0.25)
    await service.stop()

    assert calls >= 2


@pytest.mark.asyncio
async def test_interrupted_cycle_starts_next_immediately(settings: Settings) -> None:
    calls = 0

    async def cycle_behavior(**_: object) -> list[CheckResult]:
        nonlocal calls
        calls += 1
        if calls == 1:
            await asyncio.sleep(3600)
        return []

    orchestrator = MagicMock()
    orchestrator.run_full_cycle = cycle_behavior
    orchestrator.request_abort = MagicMock()
    orchestrator.clear_abort = MagicMock()
    orchestrator.fail_incomplete_checks = AsyncMock()

    service = ContinuousMonitoringService(settings, orchestrator, MagicMock())
    settings.max_check_duration_seconds = 0.05
    settings.feed_download_interval = 10_000

    service.start()
    await asyncio.sleep(0.25)
    await service.stop()

    assert calls >= 2
