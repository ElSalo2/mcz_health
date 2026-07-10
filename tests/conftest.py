"""Общие фикстуры pytest."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.domain.entities.feed_check import FeedCheck
from app.domain.entities.issue import Issue
from app.domain.entities.user import User
from app.domain.enums import (
    CheckStatus,
    ErrorEventType,
    FeedType,
    IssueCategory,
    Severity,
    UserStatus,
)
from app.infrastructure.database.base import create_engine, create_session_factory, init_database
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.infrastructure.database.utils import utc_now


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await init_database(engine)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(db_engine)


@pytest_asyncio.fixture
async def uow(session_factory: async_sessionmaker[AsyncSession]) -> AsyncGenerator[UnitOfWork, None]:
    async with UnitOfWork(session_factory) as unit:
        yield unit


@pytest.fixture
def sample_user() -> User:
    return User(
        id=None,
        phone="+79001234567",
        telegram_id=123456789,
        first_name="Иван",
        last_name="Петров",
        username="ivan_petrov",
        status=UserStatus.ACTIVE,
    )


@pytest.fixture
def sample_feed_check() -> FeedCheck:
    now = utc_now()
    return FeedCheck(
        id=None,
        feed_type=FeedType.PRODUCT,
        status=CheckStatus.RUNNING,
        started_at=now,
        finished_at=None,
        duration_seconds=None,
        item_count=None,
        sha256=None,
        content_size=None,
        feed_date=None,
        critical_count=0,
        warning_count=0,
        triggered_by="scheduler",
    )


@pytest.fixture
def sample_issue() -> Issue:
    return Issue(
        fingerprint="abc123fingerprint",
        severity=Severity.CRITICAL,
        category=IssueCategory.MISSING_FIELD,
        feed_type=FeedType.PRODUCT,
        message_key="MISSING_REQUIRED_FIELD",
        context={"name": "Товар 1", "field": "price"},
        object_id="SKU-001",
        object_name="Товар 1",
    )
