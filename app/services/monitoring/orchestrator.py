"""Оркестратор проверок — координирует 3 этапа."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.core.error_handler import handle_service_errors
from app.domain.entities.feed_check import FeedCheck
from app.domain.entities.issue import Issue
from app.domain.enums import CheckStatus, FeedType
from app.domain.value_objects.check_result import CheckResult
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.infrastructure.database.utils import utc_now
from app.infrastructure.http.resource_checker import ResourceChecker
from app.infrastructure.xml.extractors import FeedExtractor, ProductItem, StoreItem, resolve_store_feed_date
from app.infrastructure.xml.parser import ParsedFeed
from app.services.monitoring.change_detector import ChangeDetector
from app.services.monitoring.check_stats_builder import build_initial_stats
from app.services.monitoring.check_stats_tracker import CheckStatsTracker
from app.services.monitoring.feed_availability import FeedAvailabilityChecker
from app.services.monitoring.feed_structure import FeedStructureChecker
from app.services.monitoring.issue_breakdown import count_issues_by_type
from app.services.monitoring.issue_registry import IssueRegistry
from app.services.monitoring.price_validator import PriceValidationResult, PriceValidator
from app.services.monitoring.product_validator import ProductValidator
from app.services.monitoring.stock_validator import StockValidator
from app.services.monitoring.store_validator import StoreValidator
from app.services.monitoring.url_collector import collect_all_http_urls
from app.services.monitoring.url_throttle import UrlThrottlePlanner
from app.services.notification_service import NotificationService
from app.infrastructure.database.utils import dump_json

logger = logging.getLogger(__name__)

# Сначала магазины — фид маленький и проверка быстрая.
FEED_CHECK_ORDER = (FeedType.STORE, FeedType.PRODUCT)


@dataclass(slots=True)
class PreparedFeed:
    """Подготовленные данные фида после этапов 1–2."""

    feed_type: FeedType
    content: bytes | None = None
    parsed: ParsedFeed | None = None
    items: list[ProductItem] | list[StoreItem] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    failed: bool = False
    downloaded_at: datetime | None = None


class CheckOrchestrator:
    """Координирует полный цикл проверки фидов."""

    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker,
        availability_checker: FeedAvailabilityChecker,
        structure_checker: FeedStructureChecker,
        store_validator: StoreValidator,
        product_validator: ProductValidator,
        price_validator: PriceValidator,
        stock_validator: StockValidator,
        change_detector: ChangeDetector,
        feed_extractor: FeedExtractor,
        resource_checker: ResourceChecker,
        throttle_planner: UrlThrottlePlanner,
        notification_service: NotificationService,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._availability_checker = availability_checker
        self._structure_checker = structure_checker
        self._store_validator = store_validator
        self._product_validator = product_validator
        self._price_validator = price_validator
        self._stock_validator = stock_validator
        self._change_detector = change_detector
        self._feed_extractor = feed_extractor
        self._resource_checker = resource_checker
        self._throttle_planner = throttle_planner
        self._notification_service = notification_service
        self._running_checks: set[FeedType] = set()
        self._stats_tracker: CheckStatsTracker | None = None
        self._cycle_lock = asyncio.Lock()
        self._abort_requested = False
        self._resource_checker.set_abort_check(self._is_abort_requested)

    @property
    def is_running(self) -> bool:
        return bool(self._running_checks)

    def request_abort(self) -> None:
        """Запрашивает прерывание текущего цикла проверки."""
        self._abort_requested = True

    def clear_abort(self) -> None:
        """Сбрасывает флаг прерывания после завершения цикла."""
        self._abort_requested = False

    def _is_abort_requested(self) -> bool:
        return self._abort_requested

    def _raise_if_aborted(self) -> None:
        if self._abort_requested:
            raise asyncio.CancelledError("Цикл проверки прерван")

    @handle_service_errors
    async def run_background_check(self, feed_type: FeedType) -> CheckResult:
        """Выполняет проверку одного фида в рамках фонового цикла."""
        results = await self.run_full_cycle(triggered_by="background")
        for result in results:
            if result.feed_type == feed_type:
                return result
        raise RuntimeError(f"Результат проверки для {feed_type.value} не найден")

    @handle_service_errors
    async def run_full_cycle(self, triggered_by: str) -> list[CheckResult]:
        """Выполняет полный цикл проверки обоих фидов."""
        async with self._cycle_lock:
            self._abort_requested = False
            self._running_checks.update(FEED_CHECK_ORDER)
            self._stats_tracker = CheckStatsTracker(self._session_factory)
            self._resource_checker.set_stats_tracker(self._stats_tracker)
            try:
                prepared: dict[FeedType, PreparedFeed] = {}
                for feed_type in FEED_CHECK_ORDER:
                    self._raise_if_aborted()
                    prepared[feed_type] = await self._prepare_feed(feed_type)

                products = [
                    item
                    for item in prepared[FeedType.PRODUCT].items
                    if isinstance(item, ProductItem)
                ]
                stores = [
                    item
                    for item in prepared[FeedType.STORE].items
                    if isinstance(item, StoreItem)
                ]

                http_urls = collect_all_http_urls(products, stores, self._settings)
                cycle_http_url_count = len(http_urls)
                http_slot_seconds = self._throttle_planner.plan_for_url_count(cycle_http_url_count)

                results: list[CheckResult] = []
                for feed_type in FEED_CHECK_ORDER:
                    self._raise_if_aborted()
                    results.append(
                        await self._finalize_feed(
                            prepared[feed_type],
                            triggered_by=triggered_by,
                            http_slot_seconds=http_slot_seconds,
                            cycle_http_url_count=cycle_http_url_count,
                        )
                    )

                new_issues = [issue for result in results for issue in result.new_issues]
                resolved_issues = [
                    issue for result in results for issue in result.resolved_issues
                ]
                if new_issues:
                    await self._notification_service.notify_new_issues(new_issues)
                if resolved_issues:
                    await self._notification_service.notify_resolved_issues(resolved_issues)

                return results
            finally:
                self._resource_checker.set_stats_tracker(None)
                self._stats_tracker = None
                self._running_checks.clear()

    async def fail_incomplete_checks(self) -> None:
        """Помечает зависшие проверки как неуспешные (после сбоя или остановки процесса)."""
        finished_at = utc_now()
        async with UnitOfWork(self._session_factory) as uow:
            running_checks = await uow.checks.list_running()
            if not running_checks:
                return
            for check in running_checks:
                duration = None
                started_at = check.started_at
                if started_at is not None:
                    if started_at.tzinfo is None:
                        started_at = started_at.replace(tzinfo=finished_at.tzinfo)
                    duration = (finished_at - started_at).total_seconds()
                await uow.checks.update(
                    FeedCheck(
                        id=check.id,
                        feed_type=check.feed_type,
                        status=CheckStatus.INTERRUPTED,
                        started_at=check.started_at,
                        finished_at=finished_at,
                        duration_seconds=duration,
                        item_count=check.item_count,
                        sha256=check.sha256,
                        content_size=check.content_size,
                        feed_date=check.feed_date,
                        critical_count=check.critical_count,
                        warning_count=check.warning_count,
                        triggered_by=check.triggered_by,
                    )
                )
            logger.warning(
                "Закрыто незавершённых проверок: %s (%s)",
                len(running_checks),
                ", ".join(f"{check.feed_type.value}#{check.id}" for check in running_checks),
            )

    @handle_service_errors
    async def run_check(self, feed_type: FeedType, triggered_by: str) -> CheckResult:
        """Выполняет проверку одного фида (внутри полного цикла с общим HTTP-троттлингом)."""
        results = await self.run_full_cycle(triggered_by=triggered_by)
        for result in results:
            if result.feed_type == feed_type:
                return result
        raise RuntimeError(f"Результат проверки для {feed_type.value} не найден")

    async def _prepare_feed(self, feed_type: FeedType) -> PreparedFeed:
        prepared = PreparedFeed(feed_type=feed_type)

        availability = await self._availability_checker.check(feed_type)
        if not availability.available or not availability.content:
            if availability.issue is not None:
                prepared.issues.append(availability.issue)
            prepared.failed = True
            return prepared

        prepared.content = availability.content
        prepared.downloaded_at = utc_now()
        structure = self._structure_checker.check(availability.content, feed_type)
        if not structure.valid or structure.parsed is None:
            if structure.issue is not None:
                prepared.issues.append(structure.issue)
            prepared.failed = True
            return prepared

        prepared.parsed = structure.parsed
        if feed_type == FeedType.PRODUCT:
            prepared.items = self._feed_extractor.extract_products(structure.parsed.root)
        else:
            prepared.items = self._feed_extractor.extract_stores(structure.parsed.root)
            if prepared.parsed is not None:
                store_feed_date = resolve_store_feed_date(prepared.items)  # type: ignore[arg-type]
                if store_feed_date is not None:
                    prepared.parsed.feed_date = store_feed_date

        return prepared

    async def _finalize_feed(
        self,
        prepared: PreparedFeed,
        *,
        triggered_by: str,
        http_slot_seconds: float = 0.0,
        cycle_http_url_count: int = 0,
    ) -> CheckResult:
        started_at = prepared.downloaded_at or utc_now()
        timer = time.perf_counter()
        feed_type = prepared.feed_type
        feed_date = prepared.parsed.feed_date if prepared.parsed else None
        skip_http = False
        price_result: PriceValidationResult | None = None
        initial_stats = build_initial_stats(
            feed_type=feed_type,
            items=prepared.items,
            parsed=prepared.parsed,
            settings=self._settings,
            feed_extractor=self._feed_extractor,
            skip_http=False,
            http_slot_seconds=http_slot_seconds,
            cycle_http_url_count=cycle_http_url_count,
        )

        async with UnitOfWork(self._session_factory) as uow:
            feed_check = await uow.checks.create(
                FeedCheck(
                    id=None,
                    feed_type=feed_type,
                    status=CheckStatus.RUNNING,
                    started_at=started_at,
                    finished_at=None,
                    duration_seconds=None,
                    item_count=len(prepared.items) if prepared.items else None,
                    sha256=None,
                    content_size=None,
                    feed_date=feed_date,
                    critical_count=0,
                    warning_count=0,
                    triggered_by=triggered_by,
                    stats_json=dump_json(initial_stats.to_dict()),
                )
            )

        if self._stats_tracker is not None:
            self._stats_tracker.bind_check(feed_type, feed_check.id, initial_stats)

        issues = list(prepared.issues)
        item_count = len(prepared.items)
        sha256 = (
            ChangeDetector.compute_sha256(prepared.content)
            if prepared.content is not None
            else None
        )
        content_size = len(prepared.content) if prepared.content is not None else None

        if not prepared.failed and prepared.parsed is not None:
            async with UnitOfWork(self._session_factory) as uow:
                previous_check = await uow.checks.get_last_successful(feed_type)

            change = self._change_detector.detect(
                feed_type,
                prepared.content or b"",
                item_count,
                previous_check,
            )
            issues.extend(change.issues)
            skip_http = change.skip_deep_check
            initial_stats.skip_http = skip_http
            if skip_http:
                initial_stats.http_slot_seconds = 0.0
                initial_stats.planned_duration_seconds = 0.0

            freshness = self._change_detector.check_feed_freshness(feed_type, prepared.parsed)
            if freshness is not None:
                issues.append(freshness)

            if feed_type == FeedType.PRODUCT:
                async with UnitOfWork(self._session_factory) as uow:
                    previous_prices = await uow.product_prices.get_all()
                issues.extend(
                    await self._product_validator.validate(
                        prepared.parsed,
                        prepared.items,  # type: ignore[arg-type]
                        skip_http=skip_http,
                    )
                )
                issues.extend(self._stock_validator.validate(prepared.items))  # type: ignore[arg-type]
                price_result = self._price_validator.validate(
                    prepared.items,  # type: ignore[arg-type]
                    previous_prices,
                )
                issues.extend(price_result.issues)
            else:
                issues.extend(
                    await self._store_validator.validate(
                        prepared.parsed,
                        prepared.items,  # type: ignore[arg-type]
                        skip_http=skip_http,
                    )
                )

        async with UnitOfWork(self._session_factory) as uow:
            registry = IssueRegistry(uow.errors)
            registry_result = await registry.update(feed_type, issues)

        self._raise_if_aborted()

        duration = time.perf_counter() - timer
        finished_at = utc_now()
        status = CheckStatus.FAILED if prepared.failed else CheckStatus.SUCCESS
        critical_count = sum(1 for issue in issues if issue.severity.value == "critical")
        warning_count = sum(1 for issue in issues if issue.severity.value == "warning")
        warnings_by_type, critical_by_type = count_issues_by_type(issues)
        final_stats_json = None
        if self._stats_tracker is not None:
            await self._stats_tracker.flush()
            stats = self._stats_tracker.get_stats(feed_type)
            if stats is not None:
                stats.warnings_by_type = warnings_by_type
                stats.critical_by_type = critical_by_type
                final_stats_json = dump_json(stats.to_dict())

        async with UnitOfWork(self._session_factory) as uow:
            updated_check = await uow.checks.update(
                FeedCheck(
                    id=feed_check.id,
                    feed_type=feed_type,
                    status=status,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_seconds=duration,
                    item_count=item_count if not prepared.failed else 0,
                    sha256=sha256,
                    content_size=content_size,
                    feed_date=feed_date,
                    critical_count=critical_count,
                    warning_count=warning_count,
                    triggered_by=triggered_by,
                    stats_json=final_stats_json,
                )
            )
            if price_result is not None:
                await uow.product_prices.upsert_many(price_result.valid_prices)

        return CheckResult(
            feed_type=feed_type,
            feed_check=updated_check,
            issues=issues,
            new_issues=registry_result.new_issues,
            resolved_issues=registry_result.resolved_issues,
            skipped=prepared.failed,
            finished_at=finished_at,
        )
