"""Создание и настройка aiogram Dispatcher."""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.filters.admin import IsAdminFilter
from app.bot.handlers import admin, checks, menu, start
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.middlewares.container import ContainerMiddleware
from app.bot.middlewares.logging import LoggingMiddleware
from app.core.config import Settings
from app.core.container import AppContainer


def create_bot(settings: Settings) -> Bot:
    """Создаёт экземпляр Telegram-бота."""
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(container: AppContainer) -> Dispatcher:
    """Создаёт и настраивает Dispatcher с роутерами и middleware."""
    dispatcher = Dispatcher(storage=MemoryStorage())
    admin_filter = IsAdminFilter(container.config)

    dispatcher.update.middleware(LoggingMiddleware())
    dispatcher.update.middleware(ContainerMiddleware(container))

    dispatcher.include_router(start.router)

    auth_middleware = AuthMiddleware()
    protected_routers = (menu.router, checks.router)
    for protected_router in protected_routers:
        protected_router.message.middleware(auth_middleware)
        protected_router.callback_query.middleware(auth_middleware)
        dispatcher.include_router(protected_router)

    admin.router.message.filter(admin_filter)
    admin.router.callback_query.filter(admin_filter)
    admin.router.message.middleware(auth_middleware)
    admin.router.callback_query.middleware(auth_middleware)
    dispatcher.include_router(admin.router)

    return dispatcher
