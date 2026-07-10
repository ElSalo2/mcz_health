"""Форматирование данных для Telegram."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.domain.entities.feed_check import FeedCheck
from app.domain.enums import CheckStatus, FeedType
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


def format_problems_summary(critical: int, warnings: int) -> str:
    """Форматирует краткое описание найденных проблем."""
    if critical == 0 and warnings == 0:
        return Messages.PROBLEMS_NONE
    return Messages.PROBLEMS_FOUND.format(critical=critical, warnings=warnings)


def format_feed_check_summary(check: FeedCheck) -> str:
    """Форматирует краткую сводку одной проверки."""
    feed_label = FEED_TYPE_LABELS.get(check.feed_type, check.feed_type.value)

    if check.status == CheckStatus.RUNNING:
        return Messages.CHECK_SUMMARY_RUNNING.format(
            feed_name=feed_label,
            started_at=format_datetime_moscow(check.started_at),
        )

    return Messages.CHECK_SUMMARY_ITEM.format(
        feed_name=feed_label,
        status=STATUS_LABELS.get(check.status, check.status.value),
        item_count=format_item_count(check.item_count, check.feed_type),
        problems=format_problems_summary(check.critical_count, check.warning_count),
        feed_date=format_feed_date(check.feed_date),
        started_at=format_datetime_moscow(check.started_at),
        finished_at=format_datetime_moscow(check.finished_at)
        if check.finished_at
        else Messages.FINISHED_AT_UNKNOWN,
        duration=format_duration(check.duration_seconds),
    )


def format_last_check_report(
    product_check: FeedCheck | None,
    store_check: FeedCheck | None,
) -> str:
    """Форматирует отчёт о последних проверках."""
    if product_check is None and store_check is None:
        return Messages.NO_DATA

    parts = [Messages.LAST_CHECK_HEADER]
    if store_check is not None:
        parts.append(format_feed_check_summary(store_check))
    if product_check is not None:
        parts.append(format_feed_check_summary(product_check))
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
                problems=format_problems_summary(check.critical_count, check.warning_count),
                started_at=format_datetime_moscow(check.started_at),
                finished_at=format_datetime_moscow(check.finished_at)
                if check.finished_at
                else Messages.FINISHED_AT_UNKNOWN,
                duration=format_duration(check.duration_seconds),
            )
        )
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
