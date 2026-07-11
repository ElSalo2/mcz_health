"""Тесты защиты от повторного запуска."""

from app.core.single_instance import is_port_available


def test_is_port_available_on_free_port() -> None:
    assert is_port_available("127.0.0.1", 0) is True
