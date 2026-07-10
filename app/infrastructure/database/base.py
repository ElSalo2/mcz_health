"""Инициализация SQLAlchemy engine и session factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Базовый класс ORM-моделей."""


def create_engine(database_url: str) -> AsyncEngine:
    """Создаёт асинхронный движок SQLAlchemy с настройками для SQLite."""
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_async_engine(
        database_url,
        echo=False,
        connect_args=connect_args,
        pool_pre_ping=True,
    )

    if database_url.startswith("sqlite"):

        @event.listens_for(engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ARG001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Создаёт фабрику асинхронных сессий."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


async def init_database(engine: AsyncEngine) -> None:
    """Создаёт таблицы в базе данных, если они отсутствуют."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _apply_sqlite_migrations(conn)
        logger.info("База данных инициализирована")
    except Exception as exc:
        raise DatabaseError("Не удалось инициализировать базу данных", details={"error": str(exc)}) from exc


async def _apply_sqlite_migrations(conn) -> None:
    """Добавляет новые колонки в существующие таблицы SQLite."""
    if not str(conn.engine.url).startswith("sqlite"):
        return

    result = await conn.execute(text("PRAGMA table_info(feed_checks)"))
    columns = {row[1] for row in result.fetchall()}
    if "content_size" not in columns:
        await conn.execute(text("ALTER TABLE feed_checks ADD COLUMN content_size INTEGER"))


async def verify_database_connection(engine: AsyncEngine) -> None:
    """Проверяет доступность базы данных."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise DatabaseError("База данных недоступна", details={"error": str(exc)}) from exc


async def vacuum_database(engine: AsyncEngine) -> None:
    """Сжимает файл SQLite после массового удаления данных."""
    if not str(engine.url).startswith("sqlite"):
        return

    logger.info("Выполняется обслуживание базы данных (checkpoint + VACUUM)...")
    async with engine.connect() as connection:
        await connection.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
        await connection.commit()

    async with engine.connect() as connection:
        await connection.execution_options(isolation_level="AUTOCOMMIT")
        await connection.execute(text("VACUUM"))


@asynccontextmanager
async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Контекстный менеджер сессии с commit/rollback."""
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
