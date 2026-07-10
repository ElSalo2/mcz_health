"""Middleware внедрения зависимостей."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.container import AppContainer


class ContainerMiddleware(BaseMiddleware):
    """Внедряет зависимости приложения в контекст обработчиков."""

    def __init__(self, container: AppContainer) -> None:
        self._container = container

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["container"] = self._container
        data["config"] = self._container.config
        data["auth_service"] = self._container.auth_service
        data["user_service"] = self._container.user_service
        data["notification_service"] = self._container.notification_service
        data["check_query_service"] = self._container.check_query_service
        data["admin_panel_service"] = self._container.admin_panel_service
        return await handler(event, data)
