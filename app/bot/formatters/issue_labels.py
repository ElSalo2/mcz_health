"""Человекочитаемые названия типов проблем для отчётов."""

from __future__ import annotations

ISSUE_TYPE_LABELS: dict[str, str] = {
    "CATEGORY_EMPTY": "Категория без товара",
    "CATEGORY_INVALID_PARENT": "некорректный родитель категории",
    "PRODUCT_INVALID_CATEGORY": "товар ссылается на неизвестную категорию",
    "PRODUCT_MISSING_CATEGORY": "у товара нет категории",
    "PRODUCT_LOW_PRICE": "подозрительно низкая цена",
    "PRODUCT_INVALID_OLDPRICE": "некорректная старая цена",
    "PRODUCT_PRICE_CHANGE": "резкое изменение цены",
    "PRODUCT_NEGATIVE_STOCK": "отрицательный остаток",
    "PRODUCT_AVAILABLE_AT_ZERO_STOCK": "товар доступен при нулевом остатке",
    "PRODUCT_INVALID_NAME": "пустое название товара",
    "PRODUCT_MISSING_URL": "у товара нет URL",
    "DUPLICATE_URLS": "дубли URL товаров",
    "COUNT_CHANGE": "резкое изменение количества объектов",
    "FEED_SIZE_CHANGE": "резкое изменение размера фида",
    "STALE_DATA": "устаревшие данные",
    "MISSING_REQUIRED_FIELD": "отсутствует обязательное поле",
    "PRODUCT_IMAGE_INVALID_CONTENT_TYPE": "неверный Content-Type изображения",
    "PRODUCT_IMAGE_EMPTY": "пустое изображение",
    "STORE_IMAGE_INVALID_CONTENT_TYPE": "неверный Content-Type фото магазина",
    "DUPLICATE_IDS": "дубли идентификаторов",
}


def issue_type_label(message_key: str) -> str:
    """Возвращает краткое описание типа проблемы."""
    return ISSUE_TYPE_LABELS.get(message_key, message_key)
