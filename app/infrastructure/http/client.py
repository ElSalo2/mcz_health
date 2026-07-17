"""Обёртка над httpx.AsyncClient."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

DEFAULT_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

WAF_BODY_PEEK_BYTES = 1024


@dataclass(slots=True)
class HttpResponse:
    """Результат HTTP-запроса."""

    url: str
    status_code: int | None
    content_type: str | None
    content_length: int | None
    content: bytes | None = None
    error: str | None = None


class HttpClient:
    """Асинхронный HTTP-клиент с настроенными таймаутами."""

    def __init__(self, timeout: float) -> None:
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        """Инициализирует клиент."""
        limits = httpx.Limits(max_connections=1, max_keepalive_connections=1)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            limits=limits,
            follow_redirects=True,
            headers=DEFAULT_BROWSER_HEADERS,
        )

    async def stop(self) -> None:
        """Закрывает клиент."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def head(self, url: str) -> HttpResponse:
        """Выполняет HEAD-запрос."""
        client = self.raw_client
        try:
            response = await client.head(url)
            return HttpResponse(
                url=url,
                status_code=response.status_code,
                content_type=response.headers.get("content-type"),
                content_length=_parse_content_length(response.headers.get("content-length")),
            )
        except Exception as exc:
            return HttpResponse(
                url=url,
                status_code=None,
                content_type=None,
                content_length=None,
                error=str(exc),
            )

    async def get_range(self, url: str) -> HttpResponse:
        """Выполняет лёгкий GET с Range: bytes=0-0."""
        client = self.raw_client
        try:
            response = await client.get(url, headers={"Range": "bytes=0-0"})
            return HttpResponse(
                url=url,
                status_code=response.status_code,
                content_type=response.headers.get("content-type"),
                content_length=_parse_content_length(response.headers.get("content-length")),
                content=response.content[:WAF_BODY_PEEK_BYTES],
            )
        except Exception as exc:
            return HttpResponse(
                url=url,
                status_code=None,
                content_type=None,
                content_length=None,
                error=str(exc),
            )

    async def get_bytes(self, url: str) -> HttpResponse:
        """Выполняет GET-запрос и возвращает метаданные и тело ответа."""
        client = self.raw_client
        try:
            response = await client.get(url)
            return HttpResponse(
                url=url,
                status_code=response.status_code,
                content_type=response.headers.get("content-type"),
                content_length=len(response.content),
                content=response.content,
            )
        except Exception as exc:
            return HttpResponse(
                url=url,
                status_code=None,
                content_type=None,
                content_length=None,
                error=str(exc),
            )

    @property
    def raw_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("HTTP-клиент не инициализирован")
        return self._client


def _parse_content_length(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
