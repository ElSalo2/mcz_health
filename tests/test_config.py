"""Тесты конфигурации."""

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import PROJECT_ROOT, Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    """Сбрасывает кэш настроек перед каждым тестом."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _base_env() -> dict[str, str]:
    return {
        "BOT_TOKEN": "1234567890:ABCDEFghijklmnopQRSTUVwxyz",
        "ADMIN_ID": "987654321",
        "STORE_FEED_URL": "https://st.sunlight.net/media/feed/outlets/yandex_outlets_mcz.xml",
        "PRODUCT_FEED_URL": "https://st.sunlight.net/media/feed/anyquery_mcz.xml",
    }


def test_settings_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _base_env().items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("MAX_CHECK_DURATION_SECONDS", "18000")
    monkeypatch.setenv("FEED_DOWNLOAD_INTERVAL", "18000")

    settings = Settings()

    assert settings.bot_token == _base_env()["BOT_TOKEN"]
    assert settings.admin_id == 987654321
    assert settings.check_mode == "FAST"
    assert settings.check_product_images is True
    assert settings.check_social_links is False
    assert settings.local_check_reserve_seconds == 600
    assert settings.http_check_budget_seconds == 17400.0
    assert settings.data_retention_days == 3
    assert settings.log_retention_days == 3
    assert settings.db_cleanup_interval == 86400


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _base_env().items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("FEED_DOWNLOAD_INTERVAL", "18000")
    monkeypatch.setenv("ADMIN_CONTACT_PHONE", "")
    monkeypatch.setenv("MAX_CHECK_DURATION_SECONDS", "43200")

    settings = Settings()

    assert settings.feed_download_interval == 18000
    assert settings.max_check_duration_seconds == 43200
    assert settings.admin_telegram_handle == "@el_salo"
    assert settings.admin_telegram_url == "https://t.me/el_salo"
    assert settings.admin_contact_phone_normalized is None
    assert settings.log_level == "INFO"
    assert settings.database_url == "sqlite+aiosqlite:///./data/catalog_monitor.db"


def test_access_request_bypass_telegram_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _base_env().items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("ACCESS_REQUEST_BYPASS_TELEGRAM_IDS", "401627435, 999")

    settings = Settings()

    assert settings.access_request_rate_limit_bypass_ids == frozenset({401627435, 999})
    assert settings.bypasses_access_request_rate_limit(401627435) is True
    assert settings.bypasses_access_request_rate_limit(123) is False


def test_invalid_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    env = _base_env()
    env["LOG_LEVEL"] = "VERBOSE"
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    with pytest.raises(ValidationError, match="LOG_LEVEL"):
        Settings()


def test_empty_bot_token(monkeypatch: pytest.MonkeyPatch) -> None:
    env = _base_env()
    env["BOT_TOKEN"] = "   "
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    with pytest.raises(ValidationError):
        Settings()


def test_placeholder_bot_token_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    env = _base_env()
    env["BOT_TOKEN"] = "your_bot_token_here"
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    with pytest.raises(ValidationError, match="заглушку"):
        Settings()


def test_check_mode_full(monkeypatch: pytest.MonkeyPatch) -> None:
    env = _base_env()
    env["CHECK_MODE"] = "FULL"
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    settings = Settings()
    assert settings.is_full_mode is True


def test_get_feed_url_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _base_env().items():
        monkeypatch.setenv(key, value)

    settings = Settings()

    assert "anyquery_mcz.xml" in settings.get_feed_url("product")
    assert "yandex_outlets_mcz.xml" in settings.get_feed_url("store")
    assert settings.get_feed_age_limit_minutes("product") == 180
    assert settings.get_count_change_limit_percent("store") == 20
    assert settings.should_check_images("product") is True


def test_resolved_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _base_env().items():
        monkeypatch.setenv(key, value)

    settings = Settings()
    resolved = settings.get_resolved_database_url()

    assert resolved.startswith("sqlite+aiosqlite:///")
    assert "catalog_monitor.db" in resolved
    assert settings.get_sqlite_path() is not None


def test_ensure_directories(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for key, value in _base_env().items():
        monkeypatch.setenv(key, value)

    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)

    assert settings.data_dir.exists()
    assert settings.logs_dir.exists()


def test_project_root_points_to_catalog_monitor() -> None:
    assert PROJECT_ROOT.name == "catalog_monitor"
    assert (PROJECT_ROOT / "app" / "core" / "config.py").exists()
