"""Контейнер зависимостей приложения."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.config import Settings
from app.services.monitoring.factory import build_monitoring_stack

if TYPE_CHECKING:
    from aiogram import Bot
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.infrastructure.database.manager import DatabaseManager
    from app.infrastructure.http.client import HttpClient
    from app.services.admin_panel_service import AdminPanelService
    from app.services.auth_service import AuthService
    from app.services.check_query_service import CheckQueryService
    from app.services.continuous_monitoring_service import ContinuousMonitoringService
    from app.services.monitoring.orchestrator import CheckOrchestrator
    from app.services.notification_service import NotificationService
    from app.services.user_service import UserService


@dataclass(slots=True)
class AppContainer:
    """Единая точка доступа ко всем зависимостям приложения."""

    config: Settings
    session_factory: async_sessionmaker[AsyncSession]
    database_manager: DatabaseManager
    bot: Bot
    auth_service: AuthService
    user_service: UserService
    notification_service: NotificationService
    check_query_service: CheckQueryService
    admin_panel_service: AdminPanelService
    http_client: HttpClient | None = None
    check_orchestrator: CheckOrchestrator | None = None
    continuous_monitoring: ContinuousMonitoringService | None = None
    scheduler: AsyncIOScheduler | None = None


async def create_container(config: Settings) -> AppContainer:
    """Создаёт и связывает зависимости приложения."""
    from app.bot.dispatcher import create_bot
    from app.infrastructure.database.manager import DatabaseManager
    from app.services.admin_panel_service import AdminPanelService
    from app.services.auth_service import AuthService
    from app.services.check_query_service import CheckQueryService
    from app.services.notification_service import NotificationService
    from app.services.user_service import UserService

    database_manager = DatabaseManager(config)
    await database_manager.startup()

    bot = create_bot(config)
    notification_service = NotificationService(
        bot,
        config,
        session_factory=database_manager.session_factory,
    )
    auth_service = AuthService(
        database_manager.session_factory,
        notification_service,
        config,
    )
    user_service = UserService(database_manager.session_factory, config)
    check_query_service = CheckQueryService(database_manager.session_factory)
    admin_panel_service = AdminPanelService(
        user_service,
        database_manager.session_factory,
    )

    http_client, check_orchestrator, continuous_monitoring = await build_monitoring_stack(
        config,
        database_manager.session_factory,
        notification_service,
    )

    return AppContainer(
        config=config,
        session_factory=database_manager.session_factory,
        database_manager=database_manager,
        bot=bot,
        auth_service=auth_service,
        user_service=user_service,
        notification_service=notification_service,
        check_query_service=check_query_service,
        admin_panel_service=admin_panel_service,
        http_client=http_client,
        check_orchestrator=check_orchestrator,
        continuous_monitoring=continuous_monitoring,
    )


async def shutdown_container(container: AppContainer) -> None:
    """Корректно останавливает компоненты приложения."""
    if container.continuous_monitoring is not None:
        await container.continuous_monitoring.stop()

    if container.scheduler is not None:
        container.scheduler.shutdown(wait=False)

    await container.bot.session.close()
    await container.database_manager.shutdown()

    if container.http_client is not None:
        await container.http_client.stop()
