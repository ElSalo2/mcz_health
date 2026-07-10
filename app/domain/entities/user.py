"""Сущность пользователя системы."""

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import UserStatus


@dataclass(slots=True)
class User:
    """Авторизованный пользователь Telegram."""

    id: int | None
    phone: str
    telegram_id: int
    first_name: str | None
    last_name: str | None
    username: str | None
    status: UserStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE
