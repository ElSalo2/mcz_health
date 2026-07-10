"""Тесты контроля срока хранения данных."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.domain.entities.feed_check import FeedCheck
from app.domain.entities.issue import Issue
from app.domain.enums import (
    CheckStatus,
    ErrorEventType,
    FeedType,
    IssueCategory,
    Severity,
)
from app.infrastructure.database.models import (
    AuthorizationLogModel,
    ErrorHistoryModel,
    FeedCheckModel,
)
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.infrastructure.database.utils import utc_now
from app.services.retention_service import RetentionService


async def _insert_old_authorization_log(session: AsyncSession, days_ago: int) -> None:
    created_at = datetime.now(UTC) - timedelta(days=days_ago)
    session.add(
        AuthorizationLogModel(
            telegram_id=111,
            phone="+79001112233",
            success=False,
            reason="test",
            created_at=created_at,
        )
    )
    await session.flush()


async def _insert_old_feed_check(session: AsyncSession, days_ago: int) -> None:
    started_at = datetime.now(UTC) - timedelta(days=days_ago)
    session.add(
        FeedCheckModel(
            feed_type=FeedType.PRODUCT.value,
            status=CheckStatus.SUCCESS.value,
            started_at=started_at,
            finished_at=started_at,
            duration_seconds=1.0,
            item_count=10,
            sha256="abc",
            critical_count=0,
            warning_count=0,
            triggered_by="test",
        )
    )
    await session.flush()


async def _insert_old_error_history(session: AsyncSession, days_ago: int) -> None:
    created_at = datetime.now(UTC) - timedelta(days=days_ago)
    session.add(
        ErrorHistoryModel(
            fingerprint="old-error",
            event_type=ErrorEventType.OPENED.value,
            context_json="{}",
            created_at=created_at,
        )
    )
    await session.flush()


@pytest.mark.asyncio
async def test_retention_purges_old_records(
    session_factory: async_sessionmaker[AsyncSession],
    db_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    monkeypatch.setenv("DATA_RETENTION_DAYS", "3")

    settings = Settings()

    async with session_factory() as session:
        await _insert_old_authorization_log(session, days_ago=10)
        await _insert_old_feed_check(session, days_ago=10)
        await _insert_old_error_history(session, days_ago=10)
        await session.commit()

    async with UnitOfWork(session_factory) as uow:
        await uow.checks.create(
            FeedCheck(
                id=None,
                feed_type=FeedType.PRODUCT,
                status=CheckStatus.SUCCESS,
                started_at=utc_now(),
                finished_at=utc_now(),
                duration_seconds=1.0,
                item_count=1,
                sha256="fresh",
                content_size=None,
                feed_date=None,
                critical_count=0,
                warning_count=0,
                triggered_by="test",
            )
        )

    async with UnitOfWork(session_factory) as uow:
        service = RetentionService(settings, uow, db_engine)
        result = await service.run_cleanup()

    assert result.purge_stats.authorization_log == 1
    assert result.purge_stats.feed_checks == 1
    assert result.purge_stats.error_history == 1

    async with UnitOfWork(session_factory) as uow:
        counts = await uow.retention.count_records()
        assert counts["authorization_log"] == 0
        assert counts["feed_checks"] == 1
        assert counts["error_history"] == 0


@pytest.mark.asyncio
async def test_retention_purges_stale_active_errors(
    session_factory: async_sessionmaker[AsyncSession],
    db_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    settings = Settings()
    old_time = datetime.now(UTC) - timedelta(days=10)

    async with session_factory() as session:
        from app.infrastructure.database.models import ActiveErrorModel

        session.add(
            ActiveErrorModel(
                fingerprint="stale-error",
                severity=Severity.CRITICAL.value,
                category=IssueCategory.MISSING_FIELD.value,
                feed_type=FeedType.PRODUCT.value,
                context_json="{}",
                first_seen=old_time,
                last_seen=old_time,
                notified=True,
            )
        )
        await session.commit()

    async with UnitOfWork(session_factory) as uow:
        service = RetentionService(settings, uow, db_engine)
        result = await service.run_cleanup()

    assert result.purge_stats.active_errors == 1


@pytest.mark.asyncio
async def test_retention_keeps_recent_active_errors(
    session_factory: async_sessionmaker[AsyncSession],
    db_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    settings = Settings()
    issue = Issue(
        fingerprint="fresh-error",
        severity=Severity.CRITICAL,
        category=IssueCategory.URL_UNAVAILABLE,
        feed_type=FeedType.PRODUCT,
        message_key="PRODUCT_PAGE_UNAVAILABLE",
        context={},
    )

    async with UnitOfWork(session_factory) as uow:
        await uow.errors.upsert_active_error(issue)

    async with UnitOfWork(session_factory) as uow:
        service = RetentionService(settings, uow, db_engine)
        result = await service.run_cleanup()

    assert result.purge_stats.active_errors == 0

    async with UnitOfWork(session_factory) as uow:
        active = await uow.errors.get_active_by_fingerprint("fresh-error")
        assert active is not None


def test_cleanup_log_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setenv("LOG_RETENTION_DAYS", "3")

    settings = Settings()
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    old_log = logs_dir / "catalog_monitor.log.1"
    old_log.write_text("old", encoding="utf-8")
    old_mtime = (datetime.now(UTC) - timedelta(days=10)).timestamp()
    import os

    os.utime(old_log, (old_mtime, old_mtime))

    fresh_log = logs_dir / "catalog_monitor.log"
    fresh_log.write_text("fresh", encoding="utf-8")

    class DummyUow:
        session = None

    service = RetentionService(settings, DummyUow(), engine=None)  # type: ignore[arg-type]
    removed = service.cleanup_log_files(logs_dir)

    assert removed == 1
    assert not old_log.exists()
    assert fresh_log.exists()
