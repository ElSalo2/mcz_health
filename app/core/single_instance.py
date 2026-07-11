"""Проверка единственного экземпляра приложения."""

from __future__ import annotations

import socket

DEFAULT_API_PORT = 8000


def is_port_available(host: str, port: int) -> bool:
    """Возвращает True, если порт свободен для bind."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True
