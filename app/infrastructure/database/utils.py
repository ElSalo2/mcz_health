"""Вспомогательные функции для работы с базой данных."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any


def utc_now() -> datetime:
    """Возвращает текущее время в UTC."""
    return datetime.now(UTC)


def normalize_phone(phone: str) -> str:
    """
    Нормализует номер телефона к формату +<цифры>.

    Telegram может передавать номер без «+», с пробелами и скобками.
    """
    digits = re.sub(r"\D", "", phone.strip())
    if not digits:
        raise ValueError("Номер телефона не содержит цифр")
    return f"+{digits}"


def dump_json(data: dict[str, Any]) -> str:
    """Сериализует словарь в JSON для хранения в БД."""
    return json.dumps(data, ensure_ascii=False, default=str)


def load_json(raw: str) -> dict[str, Any]:
    """Десериализует JSON из БД."""
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("Ожидался JSON-объект")
    return loaded
