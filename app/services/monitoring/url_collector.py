"""Сбор URL для HTTP-проверки из распарсенных фидов."""

from __future__ import annotations

from app.core.config import Settings
from app.infrastructure.xml.extractors import ProductItem, StoreItem


def _append_unique(urls: list[str], seen: set[str], value: str | None) -> None:
    if not value:
        return
    normalized = value.strip()
    if not normalized or normalized in seen:
        return
    seen.add(normalized)
    urls.append(normalized)


def store_page_urls(store: StoreItem) -> list[str]:
    """Возвращает уникальные URL страниц магазина (url и info-page без дублей)."""
    urls: list[str] = []
    for value in (store.url, store.info_page):
        if value and value not in urls:
            urls.append(value)
    return urls


def collect_product_http_urls(products: list[ProductItem], settings: Settings) -> list[str]:
    """Собирает URL товаров для HTTP-проверки."""
    urls: list[str] = []
    seen: set[str] = set()

    for product in products:
        _append_unique(urls, seen, product.url)
        if settings.should_check_images("product"):
            for picture in product.pictures:
                _append_unique(urls, seen, picture)

    return urls


def collect_store_http_urls(stores: list[StoreItem], settings: Settings) -> list[str]:
    """Собирает URL магазинов для HTTP-проверки."""
    urls: list[str] = []
    seen: set[str] = set()

    for store in stores:
        for page_url in store_page_urls(store):
            _append_unique(urls, seen, page_url)
        if settings.check_social_links:
            for link in store.social_links:
                _append_unique(urls, seen, link)
        if settings.should_check_images("store"):
            for photo in store.photos:
                _append_unique(urls, seen, photo)

    return urls


def collect_all_http_urls(
    products: list[ProductItem],
    stores: list[StoreItem],
    settings: Settings,
) -> list[str]:
    """Собирает все уникальные URL из обоих фидов для HTTP-проверки."""
    urls: list[str] = []
    seen: set[str] = set()

    for url in collect_product_http_urls(products, settings):
        if url not in seen:
            seen.add(url)
            urls.append(url)

    for url in collect_store_http_urls(stores, settings):
        if url not in seen:
            seen.add(url)
            urls.append(url)

    return urls
