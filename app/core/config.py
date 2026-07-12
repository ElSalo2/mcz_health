"""Загрузка и валидация конфигурации из переменных окружения."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, HttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.exceptions import ConfigError

# Корень проекта: catalog_monitor/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Путь к .env относительно корня проекта
ENV_FILE_PATH = PROJECT_ROOT / ".env"

ALLOWED_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class Settings(BaseSettings):
    """Настройки приложения. Все значения загружаются из `.env`."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Telegram ---
    bot_token: str = Field(min_length=10, description="Токен Telegram-бота")
    admin_id: int = Field(gt=0, description="Telegram ID администратора")
    admin_telegram_username: str = Field(
        default="el_salo",
        min_length=1,
        description="Username администратора в Telegram (без @).",
    )
    admin_contact_phone: str | None = Field(
        default=None,
        description="Телефон администратора для карточки контакта в Telegram (например +79111112233).",
    )
    admin_contact_first_name: str = Field(
        default="Администратор",
        min_length=1,
        description="Имя в карточке контакта администратора (ваш профиль, не заявителя).",
    )
    admin_contact_last_name: str | None = Field(
        default=None,
        description="Фамилия в карточке контакта администратора.",
    )
    access_request_cooldown_seconds: int = Field(
        default=86400,
        ge=0,
        description="Минимальный интервал между заявками на доступ от одного Telegram ID (секунды).",
    )

    # --- Фиды ---
    store_feed_url: HttpUrl = Field(
        description="URL XML-фида магазинов",
    )
    product_feed_url: HttpUrl = Field(
        description="URL XML-фида товаров",
    )

    # --- База данных ---
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/catalog_monitor.db",
        description="Строка подключения SQLAlchemy",
    )

    # --- Непрерывный мониторинг ---
    feed_download_interval: int = Field(
        default=18000,
        ge=60,
        description=(
            "Устаревший параметр интервала скачивания (секунды). "
            "Новый цикл запускается сразу после завершения предыдущего."
        ),
    )
    max_check_duration_seconds: int = Field(
        default=43200,
        ge=60,
        description="Максимальная длительность одной проверки (секунды). По умолчанию 12 часов.",
    )
    local_check_reserve_seconds: int = Field(
        default=600,
        ge=0,
        description=(
            "Резерв времени на локальные проверки (парсинг XML, структура, поля). "
            "Остаток MAX_CHECK_DURATION_SECONDS отдаётся HTTP-проверкам URL."
        ),
    )

    # --- HTTP ---
    request_timeout: float = Field(default=30.0, gt=0)

    # --- Логирование ---
    log_level: str = Field(default="INFO")

    # --- Режим проверки ---
    check_mode: Literal["FAST", "FULL"] = Field(default="FAST")

    # --- Флаги проверок ---
    check_product_images: bool = Field(default=True)
    check_store_images: bool = Field(default=True)
    check_social_links: bool = Field(default=False)

    # --- Пороги ---
    max_product_feed_age_minutes: int = Field(default=180, ge=1)
    max_store_feed_age_minutes: int = Field(default=180, ge=1)
    max_product_count_change_percent: int = Field(default=20, ge=0)
    max_store_count_change_percent: int = Field(default=20, ge=0)
    max_feed_size_change_percent: int = Field(
        default=15,
        ge=0,
        description="Порог резкого изменения размера XML-фида между проверками (%)",
    )
    max_outlet_age_days: int = Field(default=3, ge=1)
    min_product_price_warning: int = Field(
        default=100,
        ge=0,
        description="Порог подозрительно низкой цены товара",
    )
    max_price_change_percent: int = Field(
        default=50,
        ge=0,
        description="Порог резкого изменения цены товара между проверками (%)",
    )

    # --- Хранение данных ---
    data_retention_days: int = Field(
        default=3,
        ge=1,
        description="Срок хранения записей в БД (дни): логи авторизации, проверки, ошибки",
    )
    log_retention_days: int = Field(
        default=3,
        ge=1,
        description="Срок хранения файлов логов (дни)",
    )
    db_cleanup_interval: int = Field(
        default=86400,
        ge=300,
        description="Интервал автоматической очистки БД (секунды)",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper().strip()
        if normalized not in ALLOWED_LOG_LEVELS:
            allowed = ", ".join(sorted(ALLOWED_LOG_LEVELS))
            raise ValueError(f"LOG_LEVEL должен быть одним из: {allowed}")
        return normalized

    @field_validator("bot_token")
    @classmethod
    def validate_bot_token(cls, value: str) -> str:
        token = value.strip()
        if not token:
            raise ValueError("BOT_TOKEN не может быть пустым")
        if token.startswith("your_") or token == "CHANGE_ME":
            raise ValueError("BOT_TOKEN содержит значение-заглушку из .env.example")
        return token

    @model_validator(mode="after")
    def validate_configuration(self) -> Settings:
        if self.local_check_reserve_seconds >= self.max_check_duration_seconds:
            raise ValueError(
                "LOCAL_CHECK_RESERVE_SECONDS должна быть меньше MAX_CHECK_DURATION_SECONDS"
            )
        return self

    @property
    def http_check_budget_seconds(self) -> float:
        """Время, выделенное на HTTP-проверки URL в одном цикле (секунды)."""
        return float(self.max_check_duration_seconds - self.local_check_reserve_seconds)

    def compute_http_url_slot_seconds(self, url_count: int) -> float:
        """
        Рассчитывает интервал между HTTP-запросами.

        (MAX_CHECK_DURATION − LOCAL_CHECK_RESERVE) / количество URL.
        """
        if url_count <= 0:
            return 0.0
        return self.http_check_budget_seconds / url_count

    @property
    def max_check_duration_minutes(self) -> int:
        """Максимальная длительность проверки в минутах (для документации)."""
        return self.max_check_duration_seconds // 60

    @property
    def admin_telegram_handle(self) -> str:
        """Username администратора с префиксом @."""
        username = self.admin_telegram_username.strip().lstrip("@")
        return f"@{username}"

    @property
    def admin_telegram_url(self) -> str:
        """Ссылка для открытия чата с администратором."""
        username = self.admin_telegram_username.strip().lstrip("@")
        return f"https://t.me/{username}"

    @property
    def admin_contact_html(self) -> str:
        """Кликабельный username администратора для HTML-сообщений."""
        return (
            f'<a href="{self.admin_telegram_url}">{self.admin_telegram_handle}</a> '
            f"(администратор)"
        )

    @property
    def admin_contact_phone_normalized(self) -> str | None:
        """Телефон администратора в формате +7... для send_contact."""
        if not self.admin_contact_phone:
            return None
        from app.infrastructure.database.utils import normalize_phone

        return normalize_phone(self.admin_contact_phone)

    @property
    def project_root(self) -> Path:
        """Корневая директория проекта."""
        return PROJECT_ROOT

    @property
    def data_dir(self) -> Path:
        """Директория для хранения данных (SQLite и др.)."""
        return PROJECT_ROOT / "data"

    @property
    def logs_dir(self) -> Path:
        """Директория для файлов логов."""
        return PROJECT_ROOT / "logs"

    @property
    def is_full_mode(self) -> bool:
        """Включён ли режим полной проверки."""
        return self.check_mode == "FULL"

    @property
    def store_feed_url_str(self) -> str:
        """URL фида магазинов в виде строки."""
        return str(self.store_feed_url)

    @property
    def product_feed_url_str(self) -> str:
        """URL фида товаров в виде строки."""
        return str(self.product_feed_url)

    @property
    def logging_level(self) -> int:
        """Числовой уровень логирования для модуля logging."""
        return getattr(logging, self.log_level, logging.INFO)

    def get_feed_url(self, feed_type: str) -> str:
        """Возвращает URL фида по типу: product | store."""
        if feed_type == "product":
            return self.product_feed_url_str
        if feed_type == "store":
            return self.store_feed_url_str
        raise ConfigError(f"Неизвестный тип фида: {feed_type}")

    def get_feed_age_limit_minutes(self, feed_type: str) -> int:
        """Возвращает максимальный возраст фида в минутах."""
        if feed_type == "product":
            return self.max_product_feed_age_minutes
        if feed_type == "store":
            return self.max_store_feed_age_minutes
        raise ConfigError(f"Неизвестный тип фида: {feed_type}")

    def get_count_change_limit_percent(self, feed_type: str) -> int:
        """Возвращает порог изменения количества объектов в процентах."""
        if feed_type == "product":
            return self.max_product_count_change_percent
        if feed_type == "store":
            return self.max_store_count_change_percent
        raise ConfigError(f"Неизвестный тип фида: {feed_type}")

    def should_check_images(self, feed_type: str) -> bool:
        """Определяет, нужно ли проверять изображения для данного типа фида."""
        if feed_type == "product":
            return self.check_product_images
        if feed_type == "store":
            return self.check_store_images
        raise ConfigError(f"Неизвестный тип фида: {feed_type}")

    def ensure_directories(self) -> None:
        """Создаёт необходимые директории, если они отсутствуют."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def get_resolved_database_url(self) -> str:
        """
        Возвращает DATABASE_URL с абсолютным путём для SQLite.

        Относительные пути разрешаются относительно корня проекта.
        Абсолютные пути используются как есть.
        """
        if not self.database_url.startswith("sqlite"):
            return self.database_url

        prefix = "sqlite+aiosqlite:///"
        if not self.database_url.startswith(prefix):
            return self.database_url

        db_path_str = self.database_url[len(prefix) :]

        # Абсолютный путь (Unix /... или Windows C:/...)
        path_candidate = Path(db_path_str)
        if path_candidate.is_absolute() or (len(db_path_str) > 1 and db_path_str[1] == ":"):
            absolute_path = Path(db_path_str).resolve()
            absolute_path.parent.mkdir(parents=True, exist_ok=True)
            return f"{prefix}{absolute_path.as_posix()}"

        if db_path_str.startswith("./"):
            db_path_str = db_path_str[2:]

        resolved = (self.project_root / db_path_str).resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return f"{prefix}{resolved.as_posix()}"

    def get_sqlite_path(self) -> Path | None:
        """Возвращает путь к файлу SQLite или None для не-SQLite БД."""
        url = self.get_resolved_database_url()
        if not url.startswith("sqlite"):
            return None
        parsed = urlparse(url.replace("sqlite+aiosqlite:", "sqlite:"))
        if parsed.path:
            return Path(parsed.path.lstrip("/"))
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Возвращает singleton-экземпляр настроек.

    Кэшируется для единообразного доступа во всём приложении.
    Для сброса кэша в тестах: get_settings.cache_clear()
    """
    settings = Settings()
    settings.ensure_directories()
    return settings


def load_settings() -> Settings:
    """
    Загружает настройки с обработкой ошибок конфигурации.

    Используется при старте приложения для понятных сообщений об ошибках.
    """
    if not ENV_FILE_PATH.exists():
        raise ConfigError(
            f"Файл {ENV_FILE_PATH} не найден. "
            "Скопируйте .env.example в .env и заполните BOT_TOKEN и ADMIN_ID:\n"
            "  Copy-Item .env.example .env"
        )
    try:
        return get_settings()
    except Exception as exc:
        raise ConfigError(
            f"Ошибка загрузки конфигурации. Проверьте файл {ENV_FILE_PATH}",
            details={"error": str(exc)},
        ) from exc
