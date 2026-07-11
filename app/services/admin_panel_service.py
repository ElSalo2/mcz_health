"""Сервис административной панели Telegram."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.error_handler import handle_service_errors
from app.domain.entities.user import User
from app.domain.enums import UserStatus
from app.locales.ru import Messages
from app.services.user_service import UserService


class AdminPanelService:
    """Операции администратора для управления пользователями."""

    def __init__(
        self,
        user_service: UserService,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._user_service = user_service
        self._session_factory = session_factory

    @handle_service_errors
    async def format_users_list(self) -> str:
        """Форматирует список пользователей для отображения."""
        users = await self._user_service.list_users()
        if not users:
            return Messages.ADMIN_NO_USERS

        lines = [Messages.ADMIN_USERS_HEADER, ""]
        for index, user in enumerate(users, start=1):
            lines.append(self._format_user_line(index, user))
        return "\n".join(lines)

    @handle_service_errors
    async def add_user_by_phone(self, phone: str) -> User:
        """Добавляет пользователя по номеру телефона."""
        return await self._user_service.add_user(phone)

    @handle_service_errors
    async def delete_user(self, user_id: int) -> User:
        """Удаляет пользователя."""
        return await self._user_service.delete_user(user_id)

    @handle_service_errors
    async def toggle_block(self, user_id: int) -> User:
        """Блокирует или разблокирует пользователя."""
        from app.infrastructure.database.unit_of_work import UnitOfWork

        async with UnitOfWork(self._session_factory) as uow:
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise ValueError("Пользователь не найден")
            if user.status == UserStatus.ACTIVE:
                return await self._user_service.block_user(user_id)
            return await self._user_service.unblock_user(user_id)

    @handle_service_errors
    async def get_user(self, user_id: int) -> User | None:
        """Возвращает пользователя по ID."""
        from app.infrastructure.database.unit_of_work import UnitOfWork

        async with UnitOfWork(self._session_factory) as uow:
            return await uow.users.get_by_id(user_id)

    @staticmethod
    def _format_user_line(index: int, user: User) -> str:
        status = "активен" if user.is_active else "заблокирован"
        telegram = "не привязан"
        if user.telegram_id:
            username = f"@{user.username}" if user.username else "без username"
            telegram = f"{username} (ID: {user.telegram_id})"
        return Messages.ADMIN_USER_ITEM.format(
            index=index,
            phone=user.phone,
            status=status,
            telegram=telegram,
        )

    @staticmethod
    def format_user_action_message(user: User, *, action: str) -> str:
        """Форматирует сообщение после действия над пользователем."""
        templates = {
            "added": Messages.ADMIN_USER_ADDED,
            "deleted": Messages.ADMIN_USER_DELETED,
            "blocked": Messages.ADMIN_USER_BLOCKED,
            "unblocked": Messages.ADMIN_USER_UNBLOCKED,
        }
        template = templates.get(action, Messages.ADMIN_ACTION_DONE)
        return template.format(phone=user.phone)
