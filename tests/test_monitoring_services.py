"""Тесты change detector и issue registry."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import Settings
from app.domain.entities.feed_check import FeedCheck
from app.domain.entities.issue import Issue
from app.domain.enums import CheckStatus, FeedType, IssueCategory, Severity
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.infrastructure.xml.parser import ParsedFeed
from app.services.monitoring.change_detector import ChangeDetector
from app.services.monitoring.issue_registry import IssueRegistry
from lxml import etree


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


def test_change_detector_skip_when_hash_unchanged(settings: Settings) -> None:
    content = b"<xml>same</xml>"
    previous = FeedCheck(
        id=1,
        feed_type=FeedType.PRODUCT,
        status=CheckStatus.SUCCESS,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        duration_seconds=1.0,
        item_count=10,
        sha256=ChangeDetector.compute_sha256(content),
        content_size=None,
        feed_date=None,
        critical_count=0,
        warning_count=0,
        triggered_by="test",
    )
    detector = ChangeDetector(settings)
    result = detector.detect(FeedType.PRODUCT, content, 10, previous)
    assert result.skip_deep_check is True


def test_change_detector_count_change_warning(settings: Settings) -> None:
    previous = FeedCheck(
        id=1,
        feed_type=FeedType.PRODUCT,
        status=CheckStatus.SUCCESS,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        duration_seconds=1.0,
        item_count=100,
        sha256="old",
        content_size=None,
        feed_date=None,
        critical_count=0,
        warning_count=0,
        triggered_by="test",
    )
    detector = ChangeDetector(settings)
    result = detector.detect(FeedType.PRODUCT, b"new", 150, previous)
    assert result.count_changed is True
    assert len(result.issues) == 1
    assert result.issues[0].category == IssueCategory.COUNT_CHANGE


def test_change_detector_feed_size_change_warning(settings: Settings) -> None:
    previous = FeedCheck(
        id=1,
        feed_type=FeedType.PRODUCT,
        status=CheckStatus.SUCCESS,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        duration_seconds=1.0,
        item_count=100,
        sha256="old",
        content_size=1000,
        feed_date=None,
        critical_count=0,
        warning_count=0,
        triggered_by="test",
    )
    detector = ChangeDetector(settings)
    result = detector.detect(FeedType.PRODUCT, b"x" * 2000, 100, previous)

    size_issues = [issue for issue in result.issues if issue.message_key == "FEED_SIZE_CHANGE"]
    assert len(size_issues) == 1


def test_check_feed_freshness(settings: Settings) -> None:
    old_date = datetime.now(UTC) - timedelta(hours=5)
    parsed = ParsedFeed(root=etree.Element("yml_catalog"), feed_date=old_date, raw_date=None)
    detector = ChangeDetector(settings)
    issue = detector.check_feed_freshness(FeedType.PRODUCT, parsed)
    assert issue is not None
    assert issue.category == IssueCategory.STALE_DATA


@pytest.mark.asyncio
async def test_issue_registry_open_and_resolve(session_factory) -> None:
    issue = Issue(
        fingerprint=IssueRegistry.build_fingerprint(
            IssueCategory.MISSING_FIELD,
            FeedType.PRODUCT,
            object_id="1",
            field="name",
        ),
        severity=Severity.CRITICAL,
        category=IssueCategory.MISSING_FIELD,
        feed_type=FeedType.PRODUCT,
        message_key="MISSING_REQUIRED_FIELD",
        object_id="1",
        object_name="Товар",
        context={"name": "Товар", "field": "name"},
    )

    async with UnitOfWork(session_factory) as uow:
        registry = IssueRegistry(uow.errors)
        opened = await registry.update(FeedType.PRODUCT, [issue])
        assert len(opened.new_issues) == 1

    async with UnitOfWork(session_factory) as uow:
        registry = IssueRegistry(uow.errors)
        resolved = await registry.update(FeedType.PRODUCT, [])
        assert len(resolved.resolved_issues) == 1
