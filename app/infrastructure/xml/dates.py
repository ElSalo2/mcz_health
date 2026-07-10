"""Парсинг дат из XML-фидов."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def parse_product_feed_date(raw_date: str | None) -> datetime | None:
    """Дата в атрибуте yml_catalog указана по московскому времени."""
    if not raw_date:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M"):
        try:
            parsed = datetime.strptime(raw_date.strip(), fmt).replace(tzinfo=MOSCOW_TZ)
            return parsed.astimezone(UTC)
        except ValueError:
            continue
    return None


def parse_outlet_date(raw_date: str | None) -> datetime | None:
    """Парсит actualization-date магазина (DD.MM.YYYY, полночь по Москве)."""
    if not raw_date:
        return None
    try:
        parsed = datetime.strptime(raw_date.strip(), "%d.%m.%Y").replace(tzinfo=MOSCOW_TZ)
        return parsed.astimezone(UTC)
    except ValueError:
        return None
