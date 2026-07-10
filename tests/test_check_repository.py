"""Тесты репозитория проверок."""

import pytest

from app.domain.entities.feed_check import FeedCheck
from app.domain.enums import CheckStatus, FeedType
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.infrastructure.database.utils import utc_now


@pytest.mark.asyncio
async def test_create_and_update_check(uow: UnitOfWork, sample_feed_check: FeedCheck) -> None:
    created = await uow.checks.create(sample_feed_check)
    assert created.id is not None
    assert created.status == CheckStatus.RUNNING

    finished_at = utc_now()
    created.status = CheckStatus.SUCCESS
    created.finished_at = finished_at
    created.duration_seconds = 12.5
    created.item_count = 1500
    created.sha256 = "deadbeef"
    created.critical_count = 2
    created.warning_count = 5

    updated = await uow.checks.update(created)
    assert updated.status == CheckStatus.SUCCESS
    assert updated.item_count == 1500


@pytest.mark.asyncio
async def test_get_last_successful(uow: UnitOfWork, sample_feed_check: FeedCheck) -> None:
    failed = sample_feed_check
    await uow.checks.create(failed)

    success = FeedCheck(
        id=None,
        feed_type=FeedType.PRODUCT,
        status=CheckStatus.SUCCESS,
        started_at=utc_now(),
        finished_at=utc_now(),
        duration_seconds=1.0,
        item_count=100,
        sha256="abc",
        content_size=None,
        feed_date=None,
        critical_count=0,
        warning_count=0,
        triggered_by="manual",
    )
    await uow.checks.create(success)

    last = await uow.checks.get_last_successful(FeedType.PRODUCT)
    assert last is not None
    assert last.status == CheckStatus.SUCCESS


@pytest.mark.asyncio
async def test_list_history(uow: UnitOfWork, sample_feed_check: FeedCheck) -> None:
    for i in range(3):
        check = FeedCheck(
            id=None,
            feed_type=FeedType.STORE if i % 2 == 0 else FeedType.PRODUCT,
            status=CheckStatus.SUCCESS,
            started_at=utc_now(),
            finished_at=utc_now(),
            duration_seconds=float(i),
            item_count=i,
            sha256=f"hash{i}",
            content_size=None,
            feed_date=None,
            critical_count=0,
            warning_count=0,
            triggered_by="scheduler",
        )
        await uow.checks.create(check)

    all_history = await uow.checks.list_history(limit=10)
    store_history = await uow.checks.list_history(FeedType.STORE, limit=10)

    assert len(all_history) == 3
    assert len(store_history) == 2
