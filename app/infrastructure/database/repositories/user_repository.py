"""Репозиторий пользователей."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseError
from app.domain.entities.user import User
from app.domain.enums import UserStatus
from app.infrastructure.database.models import AuthorizationLogModel, UserModel
from app.infrastructure.database.utils import normalize_phone, utc_now


class UserRepository:
    """Доступ к данным пользователей."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_phone(self, phone: str) -> User | None:
        """Возвращает пользователя по номеру телефона."""
        normalized = normalize_phone(phone)
        result = await self._session.execute(
            select(UserModel).where(UserModel.phone == normalized)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Возвращает пользователя по Telegram ID."""
        result = await self._session.execute(
            select(UserModel).where(UserModel.telegram_id == telegram_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_id(self, user_id: int) -> User | None:
        """Возвращает пользователя по ID."""
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(self) -> list[User]:
        """Возвращает список всех пользователей."""
        result = await self._session.execute(
            select(UserModel).order_by(UserModel.created_at.desc())
        )
        return [self._to_entity(model) for model in result.scalars().all()]

    async def list_active(self) -> list[User]:
        """Возвращает список активных пользователей с привязанным Telegram ID."""
        result = await self._session.execute(
            select(UserModel)
            .where(
                UserModel.status == UserStatus.ACTIVE.value,
                UserModel.telegram_id.is_not(None),
            )
            .order_by(UserModel.created_at.desc())
        )
        return [self._to_entity(model) for model in result.scalars().all()]

    async def create(self, user: User) -> User:
        """Создаёт нового пользователя."""
        normalized_phone = normalize_phone(user.phone)
        existing = await self.get_by_phone(normalized_phone)
        if existing is not None:
            raise DatabaseError(
                "Пользователь с таким номером телефона уже существует",
                details={"phone": normalized_phone},
            )

        model = UserModel(
            phone=normalized_phone,
            telegram_id=user.telegram_id or None,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            status=user.status.value,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def update(self, user: User) -> User:
        """Обновляет данные пользователя."""
        if user.id is None:
            raise DatabaseError("Невозможно обновить пользователя без ID")

        result = await self._session.execute(
            select(UserModel).where(UserModel.id == user.id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise DatabaseError("Пользователь не найден", details={"id": user.id})

        model.phone = normalize_phone(user.phone)
        model.telegram_id = user.telegram_id or None
        model.first_name = user.first_name
        model.last_name = user.last_name
        model.username = user.username
        model.status = user.status.value
        model.updated_at = utc_now()

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, user_id: int) -> None:
        """Удаляет пользователя."""
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise DatabaseError("Пользователь не найден", details={"id": user_id})
        await self._session.delete(model)
        await self._session.flush()

    async def had_successful_authorization(self, telegram_id: int) -> bool:
        """Проверяет, была ли у Telegram ID успешная авторизация ранее."""
        result = await self._session.execute(
            select(AuthorizationLogModel.id)
            .where(
                AuthorizationLogModel.telegram_id == telegram_id,
                AuthorizationLogModel.success.is_(True),
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def log_authorization(
        self,
        telegram_id: int,
        phone: str | None,
        success: bool,
        reason: str | None = None,
    ) -> None:
        """Записывает попытку авторизации в журнал."""
        normalized_phone = None
        if phone is not None:
            try:
                normalized_phone = normalize_phone(phone)
            except ValueError:
                normalized_phone = phone

        log_entry = AuthorizationLogModel(
            telegram_id=telegram_id,
            phone=normalized_phone,
            success=success,
            reason=reason,
        )
        self._session.add(log_entry)
        await self._session.flush()

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            phone=model.phone,
            telegram_id=model.telegram_id or 0,
            first_name=model.first_name,
            last_name=model.last_name,
            username=model.username,
            status=UserStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
