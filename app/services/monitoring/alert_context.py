"""Нормализация контекста для Telegram-алертов (без текстов сообщений)."""

from __future__ import annotations

import re
import string
from datetime import datetime
from typing import Any

from app.bot.formatters.check_formatter import format_datetime_moscow
from app.infrastructure.database.utils import utc_now
from app.infrastructure.xml.extractors import ProductItem, StoreItem

MISSING = "—"
TELEGRAM_MESSAGE_LIMIT = 4096
TRUNCATION_NOTE = (
    "\n\nПоказаны первые {shown} элементов. Полный список доступен в истории проверки."
)
IMAGE_ALERT_KEYS = frozenset(
    {
        "PRODUCT_IMAGE_UNAVAILABLE",
        "PRODUCT_IMAGE_INVALID_CONTENT_TYPE",
        "PRODUCT_IMAGE_EMPTY",
        "STORE_IMAGE_UNAVAILABLE",
        "STORE_IMAGE_INVALID_CONTENT_TYPE",
    }
)
PRODUCT_PAGE_KEYS = frozenset({"PRODUCT_PAGE_UNAVAILABLE"})


def format_duplicate_values(duplicates: dict[str, int], *, limit: int = 10) -> str:
    """Форматирует список дублей для алерта DUPLICATE_IDS."""
    items = [f"{value} (×{count})" for value, count in list(duplicates.items())[:limit]]
    return ", ".join(items) if items else MISSING


def check_datetime(value: datetime | None = None) -> str:
    """Дата и время проверки в формате ДД.ММ.ГГГГ HH:MM (МСК)."""
    return format_datetime_moscow(value or utc_now())


def product_context(product: ProductItem, **extra: Any) -> dict[str, Any]:
    """Базовые поля товара для алертов."""
    return {
        "name": product.name or MISSING,
        "offer_id": product.offer_id or MISSING,
        "product_url": product.url or MISSING,
        **extra,
    }


def store_context(store: StoreItem, **extra: Any) -> dict[str, Any]:
    """Базовые поля магазина для алертов."""
    return {
        "name": store.name or MISSING,
        "company_id": store.company_id or MISSING,
        "address": store.address or MISSING,
        **extra,
    }


def _display(value: Any) -> str:
    if value is None:
        return MISSING
    text = str(value).strip()
    return text if text else MISSING


def _parse_status_code(status: Any) -> str:
    if status is None:
        return MISSING
    if isinstance(status, int):
        return str(status)
    text = str(status).strip()
    if re.fullmatch(r"\d{3}", text):
        return text
    return MISSING


def _http_reason(status: Any) -> str:
    code = _parse_status_code(status)
    if code != MISSING:
        return f"HTTP {code}"
    text = _display(status)
    return text if text != MISSING else "Сервер не ответил или соединение прервано"


def enrich_alert_context(
    message_key: str,
    context: dict[str, Any],
    *,
    feed_url: str | None = None,
    min_price_threshold: int | None = None,
) -> dict[str, str]:
    """Приводит контекст issue к полям шаблонов messages.py."""
    raw = dict(context)
    result: dict[str, str] = {}

    for key, value in raw.items():
        result[key] = _display(value)

    if message_key != "ISSUE_RESOLVED":
        result["error_code"] = message_key

    if "check_datetime" not in result or result.get("check_datetime") == MISSING:
        check_date = result.get("check_date", MISSING)
        check_time = result.get("check_time", MISSING)
        if check_date != MISSING and check_time != MISSING:
            result["check_datetime"] = f"{check_date} {check_time}"
        elif check_date != MISSING:
            result["check_datetime"] = check_date
        else:
            result["check_datetime"] = check_datetime()

    result.setdefault("offer_id", result.get("id", MISSING))
    if message_key in IMAGE_ALERT_KEYS:
        result.setdefault("image_url", _display(raw.get("image_url") or raw.get("url")))
        result.setdefault("product_url", _display(raw.get("product_url")))
    elif message_key in PRODUCT_PAGE_KEYS:
        result.setdefault("product_url", _display(raw.get("product_url") or raw.get("url")))
    else:
        result.setdefault("product_url", _display(raw.get("product_url") or raw.get("url")))
        result.setdefault("image_url", _display(raw.get("image_url") or raw.get("url")))
    result.setdefault("image_number", result.get("number", MISSING))
    result.setdefault("company_id", result.get("id", MISSING))
    result.setdefault("status_code", _parse_status_code(raw.get("status")))
    if "reason" not in raw or raw.get("reason") in (None, ""):
        result.setdefault("reason", _http_reason(raw.get("status")))
    else:
        result["reason"] = _display(raw.get("reason"))

    if message_key in {"COUNT_CHANGE", "FEED_SIZE_CHANGE"}:
        result.setdefault("previous_count", result.get("previous", MISSING))
        result.setdefault("current_count", result.get("current", MISSING))

    if message_key == "PRODUCT_LOW_PRICE" and min_price_threshold is not None:
        result.setdefault("threshold", str(min_price_threshold))

    if message_key == "XML_UNAVAILABLE" and feed_url:
        result.setdefault("feed_url", feed_url)

    if message_key == "DUPLICATE_IDS":
        result.setdefault("id_field", result.get("field", MISSING))
        if "duplicates" not in raw or raw.get("duplicates") in (None, ""):
            count = result.get("count", MISSING)
            field = result.get("field", MISSING)
            result["duplicates"] = f"повторений: {count} (поле {field})"

    if message_key == "CATEGORY_INVALID_PARENT":
        result.setdefault("name", result.get("category_name", MISSING))
        result.setdefault("category_id", result.get("category_id", MISSING))
        result.setdefault("parent_id", result.get("parent_id", MISSING))

    if message_key == "STALE_DATA":
        result.setdefault("object_type", result.get("object_type", MISSING))
        result.setdefault("feed_date", result.get("feed_date", MISSING))
        result.setdefault("age", result.get("age", MISSING))

    if message_key == "COUNT_CHANGE":
        feed_object = raw.get("feed_type")
        if feed_object == "product":
            result.setdefault("object_type", "товары")
        elif feed_object == "store":
            result.setdefault("object_type", "магазины")
        else:
            result.setdefault("object_type", result.get("object_type", "объекты фида"))

    if message_key == "STALE_DATA" and result.get("object_type") == MISSING:
        result["object_type"] = "фид"

    if message_key == "ISSUE_RESOLVED":
        result.setdefault("object", result.get("name", result.get("offer_id", MISSING)))
        result.setdefault("description", result.get("description", "Проблема больше не воспроизводится"))
        result.setdefault("datetime", result.get("datetime", check_datetime()))

    for key, value in list(result.items()):
        if value == MISSING and key not in {
            "price",
            "oldprice",
            "duplicates",
            "description",
            "address",
            "image_number",
            "product_url",
            "image_url",
        }:
            continue
    return result


def format_alert_template(template: str, context: dict[str, str]) -> str:
    """Безопасно подставляет значения в шаблон; отсутствующие поля — «—»."""
    formatter = string.Formatter()
    field_names = {field_name for _, field_name, _, _ in formatter.parse(template) if field_name}
    safe_context = {name: context.get(name, MISSING) for name in field_names}
    return template.format(**safe_context)


def truncate_alert_text(text: str, *, max_length: int = TELEGRAM_MESSAGE_LIMIT) -> str:
    """Сокращает слишком длинное сообщение."""
    if len(text) <= max_length:
        return text
    note = TRUNCATION_NOTE.format(shown="N")
    keep = max_length - len(note) - 1
    if keep < 100:
        return text[:max_length]
    return text[:keep].rstrip() + note
