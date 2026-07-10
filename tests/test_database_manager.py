"""Тесты DatabaseManager."""

import pytest

from app.core.config import Settings
from app.infrastructure.database.manager import DatabaseManager


@pytest.mark.asyncio
async def test_database_manager_startup_shutdown(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("BOT_TOKEN", "1234567890:ABCDEFghijklmnopQRSTUVwxyz")
    monkeypatch.setenv("ADMIN_ID", "1")
    monkeypatch.setenv(
        "STORE_FEED_URL",
        "https://st.sunlight.net/media/feed/outlets/yandex_outlets_mcz.xml",
    )
    monkeypatch.setenv(
        "PRODUCT_FEED_URL",
        "https://st.sunlight.net/media/feed/anyquery_mcz.xml",
    )
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")

    settings = Settings()
    manager = DatabaseManager(settings)

    await manager.startup()
    assert db_path.exists()

    async with manager.session_factory() as session:
        assert session is not None

    await manager.shutdown()
