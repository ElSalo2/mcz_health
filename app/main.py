"""Точка входа приложения."""

from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress

from aiogram import Dispatcher
from fastapi import FastAPI
from uvicorn import Config, Server

from app.bot.dispatcher import create_dispatcher
from app.core.config import load_settings
from app.core.container import create_container, shutdown_container
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


def create_api() -> FastAPI:
    """Создаёт FastAPI-приложение."""
    from app.api.routes.health import router as health_router

    app = FastAPI(title="Catalog Monitor", version="0.1.0")
    app.include_router(health_router)
    return app


async def run_bot_polling(dispatcher: Dispatcher, bot, stop_event: asyncio.Event) -> None:
    """Запускает Telegram-бот в режиме polling."""
    try:
        await dispatcher.start_polling(bot, handle_signals=False)
    except asyncio.CancelledError:
        logger.info("Polling Telegram-бота остановлен")
    finally:
        stop_event.set()


async def main() -> None:
    """Запускает все компоненты приложения."""
    settings = load_settings()
    setup_logging(settings.log_level, settings.logs_dir)

    logger.info("Запуск системы мониторинга каталога...")
    logger.info("Режим проверки: %s", settings.check_mode)
    logger.info("База данных: %s", settings.get_resolved_database_url())

    container = await create_container(settings)
    dispatcher = create_dispatcher(container)

    if container.continuous_monitoring is not None:
        container.continuous_monitoring.start()
        logger.info("Фоновый мониторинг фидов запущен")

    stop_event = asyncio.Event()
    polling_task: asyncio.Task[None] | None = None

    def _signal_handler() -> None:
        logger.info("Получен сигнал остановки")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, _signal_handler)

    api = create_api()
    server = Server(Config(app=api, host="0.0.0.0", port=8000, log_level="warning"))

    polling_task = asyncio.create_task(run_bot_polling(dispatcher, container.bot, stop_event))
    server_task = asyncio.create_task(server.serve())

    logger.info("Приложение запущено (API + Telegram Bot)")

    await stop_event.wait()

    logger.info("Остановка приложения...")
    if polling_task is not None:
        polling_task.cancel()
        with suppress(asyncio.CancelledError):
            await polling_task

    server.should_exit = True
    await server_task
    await shutdown_container(container)
    logger.info("Приложение остановлено")


if __name__ == "__main__":
    asyncio.run(main())
