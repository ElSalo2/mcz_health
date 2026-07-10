"""Тесты репозитория ошибок."""

import pytest

from app.domain.entities.issue import Issue
from app.domain.enums import ErrorEventType, FeedType, IssueCategory, Severity
from app.infrastructure.database.unit_of_work import UnitOfWork


@pytest.mark.asyncio
async def test_upsert_and_get_active_error(uow: UnitOfWork, sample_issue: Issue) -> None:
    active = await uow.errors.upsert_active_error(sample_issue, notified=True)
    assert active.id is not None
    assert active.fingerprint == sample_issue.fingerprint

    fetched = await uow.errors.get_active_by_fingerprint(sample_issue.fingerprint)
    assert fetched is not None
    assert fetched.notified is True


@pytest.mark.asyncio
async def test_upsert_updates_last_seen(uow: UnitOfWork, sample_issue: Issue) -> None:
    first = await uow.errors.upsert_active_error(sample_issue)
    updated_issue = Issue(
        fingerprint=sample_issue.fingerprint,
        severity=Severity.WARNING,
        category=IssueCategory.STALE_DATA,
        feed_type=FeedType.PRODUCT,
        message_key="STALE_DATA",
        context={"age": "5 days"},
    )
    second = await uow.errors.upsert_active_error(updated_issue)

    assert first.id == second.id
    assert second.severity == Severity.WARNING
    assert second.last_seen >= first.last_seen


@pytest.mark.asyncio
async def test_resolve_error(uow: UnitOfWork, sample_issue: Issue) -> None:
    await uow.errors.upsert_active_error(sample_issue)
    await uow.errors.resolve_error(sample_issue.fingerprint, context={"resolved": True})

    active = await uow.errors.get_active_by_fingerprint(sample_issue.fingerprint)
    assert active is None

    history = await uow.errors.list_history(sample_issue.fingerprint)
    assert len(history) == 1
    assert history[0]["event_type"] == ErrorEventType.RESOLVED.value


@pytest.mark.asyncio
async def test_filter_active_by_feed_type(uow: UnitOfWork) -> None:
    product_issue = Issue(
        fingerprint="product-fp",
        severity=Severity.CRITICAL,
        category=IssueCategory.URL_UNAVAILABLE,
        feed_type=FeedType.PRODUCT,
        message_key="PRODUCT_PAGE_UNAVAILABLE",
        context={},
    )
    store_issue = Issue(
        fingerprint="store-fp",
        severity=Severity.CRITICAL,
        category=IssueCategory.IMAGE_UNAVAILABLE,
        feed_type=FeedType.STORE,
        message_key="STORE_IMAGE_UNAVAILABLE",
        context={},
    )
    await uow.errors.upsert_active_error(product_issue)
    await uow.errors.upsert_active_error(store_issue)

    product_errors = await uow.errors.get_active_errors(FeedType.PRODUCT)
    assert len(product_errors) == 1
    assert product_errors[0].feed_type == FeedType.PRODUCT
