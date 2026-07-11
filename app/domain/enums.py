"""Доменные перечисления."""

from enum import StrEnum


class Severity(StrEnum):
    """Уровень серьёзности проблемы."""

    CRITICAL = "critical"
    WARNING = "warning"


class FeedType(StrEnum):
    """Тип проверяемого фида."""

    PRODUCT = "product"
    STORE = "store"


class CheckMode(StrEnum):
    """Режим проверки содержимого."""

    FAST = "FAST"
    FULL = "FULL"


class CheckStatus(StrEnum):
    """Статус выполнения проверки."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    SKIPPED = "skipped"


class UserStatus(StrEnum):
    """Статус пользователя в системе."""

    ACTIVE = "active"
    BLOCKED = "blocked"


class IssueCategory(StrEnum):
    """Категория обнаруженной проблемы."""

    FEED_UNAVAILABLE = "feed_unavailable"
    FEED_PARSE = "feed_parse"
    MISSING_FIELD = "missing_field"
    DUPLICATE_ID = "duplicate_id"
    INVALID_COORDINATES = "invalid_coordinates"
    INVALID_DATE = "invalid_date"
    STALE_DATA = "stale_data"
    URL_UNAVAILABLE = "url_unavailable"
    IMAGE_UNAVAILABLE = "image_unavailable"
    INVALID_CONTENT_TYPE = "invalid_content_type"
    EMPTY_IMAGE = "empty_image"
    COUNT_CHANGE = "count_change"
    FEED_SIZE_CHANGE = "feed_size_change"
    DUPLICATE_ADDRESS = "duplicate_address"
    DUPLICATE_URL = "duplicate_url"
    INVALID_CATEGORY_PARENT = "invalid_category_parent"
    INVALID_PRODUCT_CATEGORY = "invalid_product_category"
    EMPTY_CATEGORY = "empty_category"
    INVALID_PRODUCT_NAME = "invalid_product_name"
    MISSING_URL = "missing_url"
    NEGATIVE_STOCK = "negative_stock"
    AVAILABLE_AT_ZERO_STOCK = "available_at_zero_stock"
    PRICE_MISSING = "price_missing"
    PRICE_INVALID = "price_invalid"
    PRICE_TOO_LOW = "price_too_low"
    PRICE_INVALID_OLDPRICE = "price_invalid_oldprice"
    PRICE_CHANGE = "price_change"


class ErrorEventType(StrEnum):
    """Тип события в истории ошибок."""

    OPENED = "opened"
    REOPENED = "reopened"
    RESOLVED = "resolved"
