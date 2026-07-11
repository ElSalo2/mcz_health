"""Этап 3: валидация магазинов."""

from __future__ import annotations

import logging
from collections import Counter

from app.bot.formatters.check_formatter import format_datetime_moscow
from app.core.config import Settings
from app.domain.entities.issue import Issue
from app.domain.enums import FeedType, IssueCategory, Severity
from app.domain.validators.store_rules import STORE_REQUIRED_FIELDS
from app.domain.value_objects.coordinates import Coordinates
from app.infrastructure.database.utils import utc_now
from app.infrastructure.http.resource_checker import ResourceChecker
from app.infrastructure.xml.extractors import StoreItem
from app.infrastructure.xml.parser import ParsedFeed
from app.services.monitoring.alert_context import format_duplicate_values
from app.services.monitoring.change_detector import ChangeDetector
from app.services.monitoring.image_checker import ImageChecker
from app.services.monitoring.issue_registry import IssueRegistry
from app.services.monitoring.url_collector import store_page_urls

logger = logging.getLogger(__name__)


class StoreValidator:
    """Проверяет содержимое фида магазинов."""

    def __init__(
        self,
        resource_checker: ResourceChecker,
        image_checker: ImageChecker,
        change_detector: ChangeDetector,
        settings: Settings,
    ) -> None:
        self._resource_checker = resource_checker
        self._image_checker = image_checker
        self._change_detector = change_detector
        self._settings = settings

    async def validate(
        self,
        parsed: ParsedFeed,
        stores: list[StoreItem],
        *,
        skip_http: bool = False,
    ) -> list[Issue]:
        """Выполняет все проверки магазинов."""
        issues: list[Issue] = []
        issues.extend(self._check_duplicate_ids(stores))
        issues.extend(self._check_duplicate_addresses(stores))
        check_date = format_datetime_moscow(utc_now())

        for store in stores:
            issues.extend(self._check_required_fields(store))
            issues.extend(self._check_coordinates(store))
            freshness_issue = self._change_detector.check_outlet_freshness(
                FeedType.STORE,
                store.company_id,
                store.name,
                store.actualization_datetime,
            )
            if freshness_issue is not None:
                issues.append(freshness_issue)

            if skip_http:
                continue

            for url in store_page_urls(store):
                response = await self._resource_checker.check_url(url, kind="store_page")
                if response.status_code is None or response.status_code >= 400:
                    status = (
                        str(response.status_code)
                        if response.status_code is not None
                        else (response.error or "ошибка")
                    )
                    issues.append(
                        Issue(
                            fingerprint=IssueRegistry.build_fingerprint(
                                IssueCategory.URL_UNAVAILABLE,
                                FeedType.STORE,
                                object_id=store.company_id,
                                url=url,
                            ),
                            severity=Severity.CRITICAL,
                            category=IssueCategory.URL_UNAVAILABLE,
                            feed_type=FeedType.STORE,
                            message_key="PRODUCT_PAGE_UNAVAILABLE",
                            object_id=store.company_id,
                            object_name=store.name,
                            context={
                                "id": store.company_id,
                                "name": store.name,
                                "status": status,
                                "feed_date": store.actualization_date or "—",
                                "check_date": check_date,
                            },
                        )
                    )

            if self._settings.should_check_images("store"):
                issues.extend(
                    await self._image_checker.check_images(
                        store.photos,
                        store.company_id,
                        store.name,
                        FeedType.STORE,
                        address=store.address,
                    )
                )

            if self._settings.check_social_links:
                for link in store.social_links:
                    response = await self._resource_checker.check_url(link, kind="store_page")
                    if response.status_code is None or response.status_code >= 400:
                        status = (
                            str(response.status_code)
                            if response.status_code is not None
                            else (response.error or "ошибка")
                        )
                        issues.append(
                            Issue(
                                fingerprint=IssueRegistry.build_fingerprint(
                                    IssueCategory.URL_UNAVAILABLE,
                                    FeedType.STORE,
                                    object_id=store.company_id,
                                    url=link,
                                ),
                                severity=Severity.CRITICAL,
                                category=IssueCategory.URL_UNAVAILABLE,
                                feed_type=FeedType.STORE,
                                message_key="PRODUCT_PAGE_UNAVAILABLE",
                                object_id=store.company_id,
                                object_name=store.name,
                                context={
                                    "id": store.company_id,
                                    "name": store.name,
                                    "status": status,
                                    "feed_date": store.actualization_date or "—",
                                    "check_date": check_date,
                                },
                            )
                        )

        return issues

    def _check_required_fields(self, store: StoreItem) -> list[Issue]:
        issues: list[Issue] = []
        values = {
            "company-id": store.company_id,
            "name": store.name,
            "address": store.address,
            "working-time": store.working_time,
            "photo": store.photos[0] if store.photos else "",
            "country": store.country,
            "coordinates.lat": str(store.latitude) if store.latitude is not None else "",
            "coordinates.lon": str(store.longitude) if store.longitude is not None else "",
            "url": store.url,
            "info-page": store.info_page,
            "actualization-date": store.actualization_date or "",
        }
        for field in STORE_REQUIRED_FIELDS:
            if not str(values.get(field, "")).strip():
                issues.append(self._missing_field_issue(store, field))
        return issues

    def _check_coordinates(self, store: StoreItem) -> list[Issue]:
        if store.latitude is None or store.longitude is None:
            return []
        coordinates = Coordinates(latitude=store.latitude, longitude=store.longitude)
        if coordinates.is_valid():
            return []
        return [
            Issue(
                fingerprint=IssueRegistry.build_fingerprint(
                    IssueCategory.INVALID_COORDINATES,
                    FeedType.STORE,
                    object_id=store.company_id,
                    field="coordinates",
                ),
                severity=Severity.CRITICAL,
                category=IssueCategory.INVALID_COORDINATES,
                feed_type=FeedType.STORE,
                message_key="MISSING_REQUIRED_FIELD",
                object_id=store.company_id,
                object_name=store.name,
                context={"name": store.name, "field": "coordinates"},
            )
        ]

    def _check_duplicate_ids(self, stores: list[StoreItem]) -> list[Issue]:
        counter = Counter(store.company_id for store in stores if store.company_id)
        duplicates = {company_id: count for company_id, count in counter.items() if count > 1}
        if not duplicates:
            return []
        _, count = next(iter(duplicates.items()))
        return [
            Issue(
                fingerprint=IssueRegistry.build_fingerprint(
                    IssueCategory.DUPLICATE_ID,
                    FeedType.STORE,
                    field="company-id",
                ),
                severity=Severity.CRITICAL,
                category=IssueCategory.DUPLICATE_ID,
                feed_type=FeedType.STORE,
                message_key="DUPLICATE_IDS",
                context={
                    "object_type": "магазины",
                    "field": "company-id",
                    "count": str(len(duplicates)),
                    "duplicates": format_duplicate_values(duplicates),
                },
            )
        ]

    def _check_duplicate_addresses(self, stores: list[StoreItem]) -> list[Issue]:
        counter = Counter(store.address for store in stores if store.address)
        duplicates = {address: count for address, count in counter.items() if count > 1}
        if not duplicates:
            return []
        address, count = next(iter(duplicates.items()))
        return [
            Issue(
                fingerprint=IssueRegistry.build_fingerprint(
                    IssueCategory.DUPLICATE_ADDRESS,
                    FeedType.STORE,
                    field="address",
                    url=address,
                ),
                severity=Severity.WARNING,
                category=IssueCategory.DUPLICATE_ADDRESS,
                feed_type=FeedType.STORE,
                message_key="DUPLICATE_IDS",
                context={
                    "object_type": "магазины",
                    "field": "address",
                    "count": str(len(duplicates)),
                    "duplicates": format_duplicate_values(duplicates),
                },
            )
        ]

    @staticmethod
    def _missing_field_issue(store: StoreItem, field: str) -> Issue:
        display_name = store.name or store.company_id or "магазин"
        if field == "photo":
            message_key = "STORE_MISSING_PHOTO"
            context = {
                "id": store.company_id or "—",
                "company_id": store.company_id or "—",
                "name": display_name,
                "address": store.address or "—",
                "field": field,
            }
        else:
            message_key = "MISSING_REQUIRED_FIELD"
            context = {"name": display_name, "field": field}
        return Issue(
            fingerprint=IssueRegistry.build_fingerprint(
                IssueCategory.MISSING_FIELD,
                FeedType.STORE,
                object_id=store.company_id,
                field=field,
            ),
            severity=Severity.CRITICAL,
            category=IssueCategory.MISSING_FIELD,
            feed_type=FeedType.STORE,
            message_key=message_key,
            object_id=store.company_id,
            object_name=display_name,
            context=context,
        )
