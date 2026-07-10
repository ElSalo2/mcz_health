"""Иерархия исключений приложения."""


class AppError(Exception):
    """Базовое исключение приложения."""

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigError(AppError):
    """Ошибка конфигурации."""


class DatabaseError(AppError):
    """Ошибка работы с базой данных."""


class FeedUnavailableError(AppError):
    """XML-фид недоступен."""


class FeedParseError(AppError):
    """Ошибка парсинга или структуры XML."""


class ValidationError(AppError):
    """Ошибка валидации данных каталога."""


class AuthorizationError(AppError):
    """Ошибка авторизации пользователя."""


class NotificationError(AppError):
    """Ошибка отправки уведомления."""
