"""Построение начальной статистики проверки фида."""

from __future__ import annotations

from app.core.config import Settings
from app.domain.enums import FeedType
from app.domain.value_objects.check_stats import CheckStats
from app.infrastructure.xml.extractors import FeedExtractor, ProductItem, StoreItem
from app.infrastructure.xml.parser import ParsedFeed
from app.services.monitoring.url_collector import (
    collect_product_http_urls,
    collect_store_http_urls,
    store_page_urls,
)


def _count_product_images(products: list[ProductItem], settings: Settings) -> int:
    if not settings.should_check_images("product"):
        return 0
    return sum(len(product.pictures) for product in products)


def _count_store_images(stores: list[StoreItem], settings: Settings) -> int:
    if not settings.should_check_images("store"):
        return 0
    return sum(len(store.photos) for store in stores)


def build_initial_stats(
    *,
    feed_type: FeedType,
    items: list[ProductItem] | list[StoreItem],
    parsed: ParsedFeed | None,
    settings: Settings,
    feed_extractor: FeedExtractor,
    skip_http: bool,
    http_slot_seconds: float = 0.0,
    cycle_http_url_count: int = 0,
) -> CheckStats:
    """Формирует план проверки до начала HTTP-этапа."""
    stats = CheckStats(
        items_in_feed=len(items),
        skip_http=skip_http,
        max_duration_seconds=settings.max_check_duration_seconds,
    )

    if feed_type == FeedType.PRODUCT:
        products = items  # type: ignore[assignment]
        stats.product_pages_planned = sum(1 for product in products if product.url)
        stats.product_images_planned = _count_product_images(products, settings)
        if parsed is not None:
            stats.categories_in_feed = len(feed_extractor.extract_categories(parsed.root))
        stats.categories_used_by_products = len(
            {product.category_id for product in products if product.category_id}
        )
        stats.names_checked = len(products)
        stats.required_fields_checked = len(products) * 4
        stats.stocks_checked = len(products)
        stats.prices_checked = len(products)
        stats.categories_validated = len(products)
        stats.http_total_planned = len(collect_product_http_urls(products, settings))
        _apply_http_timing_estimate(
            stats,
            settings=settings,
            skip_http=skip_http,
            http_slot_seconds=http_slot_seconds,
            cycle_http_url_count=cycle_http_url_count,
        )
        return stats

    stores = items  # type: ignore[assignment]
    stats.store_pages_planned = sum(len(store_page_urls(store)) for store in stores)
    if settings.check_social_links:
        stats.store_pages_planned += sum(len(store.social_links) for store in stores)
    stats.store_images_planned = _count_store_images(stores, settings)
    stats.required_fields_checked = len(stores) * 3
    stats.http_total_planned = len(collect_store_http_urls(stores, settings))
    _apply_http_timing_estimate(
        stats,
        settings=settings,
        skip_http=skip_http,
        http_slot_seconds=http_slot_seconds,
        cycle_http_url_count=cycle_http_url_count,
    )
    return stats


def _apply_http_timing_estimate(
    stats: CheckStats,
    *,
    settings: Settings,
    skip_http: bool,
    http_slot_seconds: float,
    cycle_http_url_count: int,
) -> None:
    """Заполняет оценку длительности HTTP-этапа по троттлингу цикла."""
    stats.http_slot_seconds = http_slot_seconds
    if skip_http or http_slot_seconds <= 0 or stats.http_total_planned <= 0:
        return

    local_share = 0.0
    if cycle_http_url_count > 0:
        local_share = settings.local_check_reserve_seconds * (
            stats.http_total_planned / cycle_http_url_count
        )
    stats.planned_duration_seconds = local_share + stats.http_total_planned * http_slot_seconds
