"""Тесты определения WAF-challenge и ResourceChecker."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.http.client import HttpResponse
from app.infrastructure.http.resource_checker import ResourceChecker
from app.infrastructure.http.waf_detection import is_waf_challenge


def test_is_waf_challenge_detects_qrator_page() -> None:
    body = b'<!DOCTYPE html><script src="/__qrator/qauth.js"></script>'
    response = HttpResponse(url="https://mczgold.ru/x", status_code=401, content_type="text/html", content_length=100, content=body)
    assert is_waf_challenge(response) is True


def test_is_waf_challenge_ignores_real_404() -> None:
    response = HttpResponse(
        url="https://mczgold.ru/missing",
        status_code=404,
        content_type="text/html",
        content_length=100,
        content=b"Not Found",
    )
    assert is_waf_challenge(response) is False


def test_is_waf_challenge_requires_body() -> None:
    response = HttpResponse(url="https://mczgold.ru/x", status_code=401, content_type="text/html", content_length=0)
    assert is_waf_challenge(response) is False


@pytest.mark.asyncio
async def test_resource_checker_treats_waf_challenge_as_available() -> None:
    http_client = MagicMock()
    http_client.head = AsyncMock(
        side_effect=[
            HttpResponse(url="https://mczgold.ru/x", status_code=401, content_type=None, content_length=None),
            HttpResponse(url="https://mczgold.ru/x", status_code=401, content_type=None, content_length=None),
        ]
    )
    http_client.get_range = AsyncMock(
        return_value=HttpResponse(
            url="https://mczgold.ru/x",
            status_code=401,
            content_type="text/html",
            content_length=265,
            content=b'<script src="/__qrator/qauth.js"></script>',
        )
    )
    throttle = MagicMock()
    throttle.slot_seconds = 0
    throttle.seconds_until_next_request = MagicMock(return_value=0)

    checker = ResourceChecker(http_client, throttle)
    response = await checker.check_url("https://mczgold.ru/x", kind="product_page")

    assert response.status_code == 200
    assert http_client.head.await_count == 2
    http_client.get_range.assert_awaited_once()


@pytest.mark.asyncio
async def test_resource_checker_keeps_real_http_error() -> None:
    http_client = MagicMock()
    http_client.head = AsyncMock(
        side_effect=[
            HttpResponse(url="https://mczgold.ru/missing", status_code=404, content_type=None, content_length=None),
            HttpResponse(url="https://mczgold.ru/missing", status_code=404, content_type=None, content_length=None),
        ]
    )
    http_client.get_range = AsyncMock(
        return_value=HttpResponse(
            url="https://mczgold.ru/missing",
            status_code=404,
            content_type="text/html",
            content_length=100,
            content=b"Not Found",
        )
    )
    throttle = MagicMock()
    throttle.slot_seconds = 0
    throttle.seconds_until_next_request = MagicMock(return_value=0)

    checker = ResourceChecker(http_client, throttle)
    response = await checker.check_url("https://mczgold.ru/missing", kind="product_page")

    assert response.status_code == 404
