"""Форматирование данных для Telegram."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.domain.entities.feed_check import FeedCheck
from app.domain.enums import CheckStatus, FeedType
from app.domain.value_objects.check_stats import CheckStats
from app.domain.value_objects.feed_check_view import FeedCheckView
from app.infrastructure.database.utils import load_json, utc_now
from app.locales.ru import Messages

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

FEED_TYPE_LABELS = {
    FeedType.PRODUCT: "Каталог товаров",
    FeedType.STORE: "Каталог магазинов",
}

STATUS_LABELS = {
    CheckStatus.RUNNING: "⏳ выполняется",
    CheckStatus.SUCCESS: "✅ завершена успешно",
    CheckStatus.FAILED: "❌ завершена с ошибкой",
    CheckStatus.INTERRUPTED: "⏹ прервана",
    CheckStatus.SKIPPED: "⏭ пропущена",
}


def format_datetime_moscow(value: datetime) -> str:
    """Форматирует дату и время в московском часовом поясе."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M")


def format_feed_date(value: datetime | None) -> str:
    """Форматирует дату формирования фида."""
    if value is None:
        return Messages.FEED_DATE_UNKNOWN
    return format_datetime_moscow(value)


def format_duration(seconds: float | None) -> str:
    """Форматирует длительность в читаемый вид."""
    if seconds is None:
        return Messages.DURATION_UNKNOWN
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours} ч {minutes} мин"
    if minutes > 0:
        return f"{minutes} мин {secs} сек"
    return f"{secs} сек"


def format_item_count(count: int | None, feed_type: FeedType) -> str:
    """Форматирует количество проверенных объектов."""
    if count is None:
        return Messages.ITEM_COUNT_UNKNOWN

    label = "товаров" if feed_type == FeedType.PRODUCT else "магазинов"
    return f"{count:,}".replace(",", " ") + f" {label}"


def format_problems_summary(critical: int, warnings: int, *, status: CheckStatus | None = None) -> str:
    """Форматирует краткое описание найденных проблем."""
    if status == CheckStatus.INTERRUPTED:
        return Messages.PROBLEMS_INTERRUPTED
    if status == CheckStatus.RUNNING:
        return Messages.PROBLEMS_IN_PROGRESS
    if critical == 0 and warnings == 0:
        return Messages.PROBLEMS_NONE
    return Messages.PROBLEMS_FOUND.format(critical=critical, warnings=warnings)


def _format_progress(checked: int, planned: int) -> str:
    if planned <= 0:
        return str(checked)
    percent = min(100, round(checked / planned * 100))
    return f"{checked:,}".replace(",", " ") + f" из {planned:,}".replace(",", " ") + f" ({percent}%)"


def _stats_from_check(check: FeedCheck) -> CheckStats:
    if not check.stats_json:
        return CheckStats()
    return CheckStats.from_dict(load_json(check.stats_json))


def estimate_planned_finish_at(
    *,
    started_at: datetime | None,
    stats: CheckStats,
    now: datetime | None = None,
) -> datetime | None:
    """Оценивает плановое окончание проверки по троттлингу URL, а не по лимиту цикла."""
    if started_at is None or stats.skip_http:
        return None

    started = started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)

    if stats.http_slot_seconds <= 0 or stats.http_total_planned <= 0:
        return None

    remaining_http = max(0, stats.http_total_planned - stats.http_total_checked)
    if stats.http_total_checked > 0 and remaining_http > 0:
        reference = now if now is not None else utc_now()
        return reference + timedelta(seconds=remaining_http * stats.http_slot_seconds)

    duration_seconds = stats.planned_duration_seconds
    if duration_seconds <= 0:
        duration_seconds = stats.http_total_planned * stats.http_slot_seconds

    if duration_seconds <= 0:
        return None

    return started + timedelta(seconds=duration_seconds)


def _format_running_timing_lines(check: FeedCheck, stats: CheckStats) -> list[str]:
    """Дополняет блок статистики сроками для выполняющейся проверки."""
    if check.status != CheckStatus.RUNNING:
        return []

    lines = [
        Messages.CHECK_STATS_FEED_DATE.format(feed_date=format_feed_date(check.feed_date)),
        Messages.CHECK_STATS_STARTED_AT.format(
            started_at=format_datetime_moscow(check.started_at)
            if check.started_at
            else Messages.FINISHED_AT_UNKNOWN,
        ),
    ]
    planned_finish = estimate_planned_finish_at(started_at=check.started_at, stats=stats)
    if planned_finish is not None:
        lines.append(
            Messages.CHECK_STATS_PLANNED_FINISH.format(
                planned_finish=format_datetime_moscow(planned_finish),
            )
        )
    return lines


def format_check_stats_block(check: FeedCheck) -> str:
    """Форматирует детальную статистику проверки."""
    stats = _stats_from_check(check)
    if stats.items_in_feed == 0 and stats.http_total_planned == 0:
        return ""

    lines: list[str] = [Messages.CHECK_STATS_HEADER]

    if check.feed_type == FeedType.PRODUCT:
        lines.append(Messages.CHECK_STATS_ITEMS.format(count=stats.items_in_feed))
        if stats.categories_in_feed:
            lines.append(Messages.CHECK_STATS_CATEGORIES.format(count=stats.categories_in_feed))
        if stats.categories_used_by_products:
            lines.append(
                Messages.CHECK_STATS_CATEGORIES_USED.format(count=stats.categories_used_by_products)
            )
        if stats.skip_http:
            lines.append(Messages.CHECK_STATS_HTTP_SKIPPED)
        else:
            if stats.product_pages_planned:
                lines.append(
                    Messages.CHECK_STATS_PRODUCT_PAGES.format(
                        progress=_format_progress(stats.product_pages_checked, stats.product_pages_planned),
                        ok=stats.product_pages_ok,
                    )
                )
            if stats.product_images_planned:
                lines.append(
                    Messages.CHECK_STATS_PRODUCT_IMAGES.format(
                        progress=_format_progress(stats.product_images_checked, stats.product_images_planned),
                        ok=stats.product_images_ok,
                    )
                )
            if stats.http_total_planned:
                lines.append(
                    Messages.CHECK_STATS_HTTP_TOTAL.format(
                        progress=_format_progress(stats.http_total_checked, stats.http_total_planned),
                        ok=stats.http_total_ok,
                    )
                )
        if stats.prices_checked:
            lines.append(Messages.CHECK_STATS_PRICES.format(count=stats.prices_checked))
        if stats.stocks_checked:
            lines.append(Messages.CHECK_STATS_STOCKS.format(count=stats.stocks_checked))
        if stats.names_checked:
            lines.append(Messages.CHECK_STATS_NAMES.format(count=stats.names_checked))
        lines.extend(_format_running_timing_lines(check, stats))
        return "\n".join(lines)

    lines.append(Messages.CHECK_STATS_STORES.format(count=stats.items_in_feed))
    if stats.skip_http:
        lines.append(Messages.CHECK_STATS_HTTP_SKIPPED)
    else:
        if stats.store_pages_planned:
            lines.append(
                Messages.CHECK_STATS_STORE_PAGES.format(
                    progress=_format_progress(stats.store_pages_checked, stats.store_pages_planned),
                    ok=stats.store_pages_ok,
                )
            )
        if stats.store_images_planned:
            lines.append(
                Messages.CHECK_STATS_STORE_IMAGES.format(
                    progress=_format_progress(stats.store_images_checked, stats.store_images_planned),
                    ok=stats.store_images_ok,
                )
            )
    lines.extend(_format_running_timing_lines(check, stats))
    return "\n".join(lines)


def format_feed_check_summary(check: FeedCheck) -> str:
    """Форматирует краткую сводку одной проверки."""
    feed_label = FEED_TYPE_LABELS.get(check.feed_type, check.feed_type.value)

    if check.status == CheckStatus.RUNNING:
        stats_block = format_check_stats_block(check)
        started = check.started_at
        if started is not None and started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        elapsed = format_duration((utc_now() - started).total_seconds() if started else None)
        parts = [
            Messages.CHECK_SUMMARY_RUNNING.format(
                feed_name=feed_label,
                started_at=format_datetime_moscow(check.started_at),
                elapsed=elapsed,
            )
        ]
        if stats_block:
            parts.append(stats_block)
        return "\n".join(parts)

    summary = Messages.CHECK_SUMMARY_ITEM.format(
        feed_name=feed_label,
        status=STATUS_LABELS.get(check.status, check.status.value),
        item_count=format_item_count(check.item_count, check.feed_type),
        problems=format_problems_summary(check.critical_count, check.warning_count, status=check.status),
        feed_date=format_feed_date(check.feed_date),
        started_at=format_datetime_moscow(check.started_at),
        finished_at=format_datetime_moscow(check.finished_at)
        if check.finished_at
        else Messages.FINISHED_AT_UNKNOWN,
        duration=format_duration(check.duration_seconds),
    )
    stats_block = format_check_stats_block(check)
    if stats_block:
        return f"{summary}\n{stats_block}"
    return summary


def format_feed_check_view(view: FeedCheckView) -> str:
    """Форматирует текущую и предыдущую проверку одного фида."""
    if view.current is None:
        return ""

    parts = [format_feed_check_summary(view.current)]
    if (
        view.previous is not None
        and view.current.status == CheckStatus.RUNNING
    ):
        parts.append(Messages.CHECK_PREVIOUS_HEADER)
        parts.append(format_feed_check_summary(view.previous))
    return "\n\n".join(parts)


def format_last_check_report(
    product_view: FeedCheckView | FeedCheck | None,
    store_view: FeedCheckView | FeedCheck | None,
) -> str:
    """Форматирует отчёт о последних проверках."""
    if isinstance(store_view, FeedCheck):
        store_view = FeedCheckView(current=store_view)
    if isinstance(product_view, FeedCheck):
        product_view = FeedCheckView(current=product_view)

    if (store_view is None or store_view.current is None) and (
        product_view is None or product_view.current is None
    ):
        return Messages.NO_DATA

    parts = [Messages.LAST_CHECK_HEADER]
    if store_view is not None and store_view.current is not None:
        parts.append(format_feed_check_view(store_view))
    if product_view is not None and product_view.current is not None:
        parts.append(format_feed_check_view(product_view))
    return "\n\n".join(parts)


def format_history_report(checks: list[FeedCheck]) -> str:
    """Форматирует историю проверок."""
    if not checks:
        return Messages.NO_DATA

    lines = [Messages.HISTORY_HEADER]
    for index, check in enumerate(checks, start=1):
        feed_label = FEED_TYPE_LABELS.get(check.feed_type, check.feed_type.value)

        if check.status == CheckStatus.RUNNING:
            lines.append(
                Messages.HISTORY_ITEM_RUNNING.format(
                    index=index,
                    feed_name=feed_label,
                    started_at=format_datetime_moscow(check.started_at),
                )
            )
            continue

        lines.append(
            Messages.HISTORY_ITEM.format(
                index=index,
                feed_name=feed_label,
                status=STATUS_LABELS.get(check.status, check.status.value),
                item_count=format_item_count(check.item_count, check.feed_type),
                problems=format_problems_summary(
                    check.critical_count,
                    check.warning_count,
                    status=check.status,
                ),
                started_at=format_datetime_moscow(check.started_at),
                finished_at=format_datetime_moscow(check.finished_at)
                if check.finished_at
                else Messages.FINISHED_AT_UNKNOWN,
                duration=format_duration(check.duration_seconds),
            )
        )
        stats_block = format_check_stats_block(check)
        if stats_block:
            lines.append(stats_block)
    return "\n\n".join(lines)


def format_check_cycle_completed(
    results: list[FeedCheck],
    total_duration: float,
) -> str:
    """Форматирует итог автоматического цикла проверки."""
    products = next((r.item_count for r in results if r.feed_type == FeedType.PRODUCT), 0) or 0
    stores = next((r.item_count for r in results if r.feed_type == FeedType.STORE), 0) or 0
    critical = sum(r.critical_count for r in results)
    warnings = sum(r.warning_count for r in results)
    return Messages.CHECK_CYCLE_COMPLETED.format(
        products=products,
        stores=stores,
        critical=critical,
        warnings=warnings,
        duration=format_duration(total_duration),
    )
