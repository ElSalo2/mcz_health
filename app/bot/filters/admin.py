"""Фильтр администратора."""

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.core.config import Settings


class IsAdminFilter(BaseFilter):
    """Пропускает только события от администратора."""

    def __init__(self, settings: Settings) -> None:
        self._admin_id = settings.admin_id

    async def __call__(self, event: TelegramObject) -> bool:
        user = None
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
        return user is not None and user.id == self._admin_id
