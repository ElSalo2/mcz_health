"""Константы и правила валидации товаров."""

PRODUCT_REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "vendor",
    "picture",
    "categoryId",
)
