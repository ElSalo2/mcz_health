"""Проверка изображений."""

from __future__ import annotations

import logging

from app.bot.formatters.check_formatter import format_datetime_moscow
from app.core.config import Settings
from app.domain.entities.issue import Issue
from app.domain.enums import FeedType, IssueCategory, Severity
from app.infrastructure.database.utils import utc_now
from app.infrastructure.http.client import HttpResponse
from app.infrastructure.http.resource_checker import ResourceChecker
from app.services.monitoring.issue_registry import IssueRegistry

logger = logging.getLogger(__name__)

IMAGE_CONTENT_PREFIX = "image/"


class ImageChecker:
    """Проверяет доступность и корректность изображений."""

    def __init__(self, resource_checker: ResourceChecker, settings: Settings) -> None:
        self._resource_checker = resource_checker
        self._settings = settings

    async def check_images(
        self,
        urls: list[str],
        object_id: str,
        object_name: str,
        feed_type: FeedType,
        *,
        feed_date: str | None = None,
        product_url: str | None = None,
        address: str | None = None,
    ) -> list[Issue]:
        """Проверяет список URL изображений."""
        issues: list[Issue] = []
        check_date = format_datetime_moscow(utc_now())

        for index, url in enumerate(urls, start=1):
            response = await self._resource_checker.check_url(url)
            image_issues = self._validate_response(
                response=response,
                object_id=object_id,
                object_name=object_name,
                feed_type=feed_type,
                url=url,
                index=index,
                check_date=check_date,
                feed_date=feed_date,
                product_url=product_url,
                address=address,
            )
            issues.extend(image_issues)

        return issues

    def _validate_response(
        self,
        *,
        response: HttpResponse,
        object_id: str,
        object_name: str,
        feed_type: FeedType,
        url: str,
        index: int,
        check_date: str,
        feed_date: str | None,
        product_url: str | None = None,
        address: str | None = None,
    ) -> list[Issue]:
        issues: list[Issue] = []
        status = str(response.status_code) if response.status_code is not None else (response.error or "ошибка")

        if response.status_code is None or response.status_code >= 400:
            message_key = (
                "PRODUCT_IMAGE_UNAVAILABLE" if feed_type == FeedType.PRODUCT else "STORE_IMAGE_UNAVAILABLE"
            )
            context: dict[str, object] = {
                "id": object_id,
                "name": object_name,
                "number": index,
                "status": status,
                "url": url,
                "image_url": url,
                "check_date": check_date,
            }
            if feed_type == FeedType.PRODUCT:
                if product_url:
                    context["product_url"] = product_url
                if feed_date:
                    context["feed_date"] = feed_date
            else:
                context["company_id"] = object_id
                if address:
                    context["address"] = address

            issues.append(
                Issue(
                    fingerprint=IssueRegistry.build_fingerprint(
                        IssueCategory.IMAGE_UNAVAILABLE,
                        feed_type,
                        object_id=object_id,
                        url=url,
                    ),
                    severity=Severity.CRITICAL,
                    category=IssueCategory.IMAGE_UNAVAILABLE,
                    feed_type=feed_type,
                    message_key=message_key,
                    object_id=object_id,
                    object_name=object_name,
                    context=context,
                )
            )
            return issues

        if self._settings.is_full_mode:
            content_type = (response.content_type or "").lower()
            if content_type and not content_type.startswith(IMAGE_CONTENT_PREFIX):
                message_key = (
                    "PRODUCT_IMAGE_INVALID_CONTENT_TYPE"
                    if feed_type == FeedType.PRODUCT
                    else "STORE_IMAGE_INVALID_CONTENT_TYPE"
                )
                issues.append(
                    Issue(
                        fingerprint=IssueRegistry.build_fingerprint(
                            IssueCategory.INVALID_CONTENT_TYPE,
                            feed_type,
                            object_id=object_id,
                            url=url,
                        ),
                        severity=Severity.WARNING,
                        category=IssueCategory.INVALID_CONTENT_TYPE,
                        feed_type=feed_type,
                        message_key=message_key,
                        object_id=object_id,
                        object_name=object_name,
                        context={
                            "id": object_id,
                            "name": object_name,
                            "number": index,
                            "status": content_type,
                            "url": url,
                            "image_url": url,
                            "check_date": check_date,
                            **({"product_url": product_url} if product_url else {}),
                            **({"company_id": object_id, "address": address} if feed_type == FeedType.STORE and address else {}),
                        },
                    )
                )

            if response.content_length == 0:
                message_key = (
                    "PRODUCT_IMAGE_EMPTY"
                    if feed_type == FeedType.PRODUCT
                    else "STORE_IMAGE_UNAVAILABLE"
                )
                category = (
                    IssueCategory.EMPTY_IMAGE
                    if feed_type == FeedType.PRODUCT
                    else IssueCategory.IMAGE_UNAVAILABLE
                )
                issues.append(
                    Issue(
                        fingerprint=IssueRegistry.build_fingerprint(
                            category,
                            feed_type,
                            object_id=object_id,
                            url=url,
                        ),
                        severity=Severity.CRITICAL if feed_type == FeedType.PRODUCT else Severity.WARNING,
                        category=category,
                        feed_type=feed_type,
                        message_key=message_key,
                        object_id=object_id,
                        object_name=object_name,
                        context={
                            "id": object_id,
                            "name": object_name,
                            "number": index,
                            "status": "пустой файл",
                            "url": url,
                            "image_url": url,
                            "check_date": check_date,
                            **({"product_url": product_url} if product_url else {}),
                            **({"company_id": object_id, "address": address} if feed_type == FeedType.STORE and address else {}),
                        },
                    )
                )

        return issues
