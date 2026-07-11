"""Unit of Work — единая транзакция для нескольких репозиториев."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.database.repositories.bot_chat_message_repository import BotChatMessageRepository
from app.infrastructure.database.repositories.check_repository import CheckRepository
from app.infrastructure.database.repositories.error_repository import ErrorRepository
from app.infrastructure.database.repositories.product_price_repository import ProductPriceRepository
from app.infrastructure.database.repositories.retention_repository import RetentionRepository
from app.infrastructure.database.repositories.settings_repository import SettingsRepository
from app.infrastructure.database.repositories.user_repository import UserRepository


class UnitOfWork:
    """Объединяет репозитории в одну транзакцию."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Сессия не инициализирована. Используйте UnitOfWork как async context manager.")
        return self._session

    @property
    def users(self) -> UserRepository:
        return UserRepository(self.session)

    @property
    def bot_chat_messages(self) -> BotChatMessageRepository:
        return BotChatMessageRepository(self.session)

    @property
    def checks(self) -> CheckRepository:
        return CheckRepository(self.session)

    @property
    def errors(self) -> ErrorRepository:
        return ErrorRepository(self.session)

    @property
    def settings(self) -> SettingsRepository:
        return SettingsRepository(self.session)

    @property
    def product_prices(self) -> ProductPriceRepository:
        return ProductPriceRepository(self.session)

    @property
    def retention(self) -> RetentionRepository:
        return RetentionRepository(self.session)

    async def __aenter__(self) -> UnitOfWork:
        self._session = self._session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        try:
            if exc_type is None:
                await self._session.commit()
            else:
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None
