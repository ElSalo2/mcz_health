"""Репозиторий настроек приложения."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import ApplicationSettingModel
from app.infrastructure.database.utils import utc_now


class SettingsRepository:
    """Доступ к таблице application_settings."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> str | None:
        """Возвращает значение настройки по ключу."""
        result = await self._session.execute(
            select(ApplicationSettingModel).where(ApplicationSettingModel.key == key)
        )
        model = result.scalar_one_or_none()
        return model.value if model else None

    async def set(self, key: str, value: str) -> None:
        """Сохраняет или обновляет настройку."""
        result = await self._session.execute(
            select(ApplicationSettingModel).where(ApplicationSettingModel.key == key)
        )
        model = result.scalar_one_or_none()

        if model is None:
            model = ApplicationSettingModel(key=key, value=value)
            self._session.add(model)
        else:
            model.value = value
            model.updated_at = utc_now()

        await self._session.flush()

    async def delete(self, key: str) -> None:
        """Удаляет настройку."""
        result = await self._session.execute(
            select(ApplicationSettingModel).where(ApplicationSettingModel.key == key)
        )
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    async def get_all(self) -> dict[str, str]:
        """Возвращает все настройки приложения."""
        result = await self._session.execute(select(ApplicationSettingModel))
        return {model.key: model.value for model in result.scalars().all()}
