"""Тесты вспомогательных функций БД."""

import pytest

from app.infrastructure.database.utils import dump_json, load_json, normalize_phone


def test_normalize_phone_with_plus() -> None:
    assert normalize_phone("+7 (900) 123-45-67") == "+79001234567"


def test_normalize_phone_without_plus() -> None:
    assert normalize_phone("79001234567") == "+79001234567"


def test_normalize_phone_empty_raises() -> None:
    with pytest.raises(ValueError, match="цифр"):
        normalize_phone("   ")


def test_json_roundtrip() -> None:
    data = {"name": "Тест", "count": 42, "nested": {"ok": True}}
    assert load_json(dump_json(data)) == data
