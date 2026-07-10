"""Константы и правила валидации магазинов."""

STORE_REQUIRED_FIELDS: tuple[str, ...] = (
    "company-id",
    "name",
    "address",
    "working-time",
    "photo",
    "country",
    "coordinates.lat",
    "coordinates.lon",
    "url",
    "info-page",
    "actualization-date",
)
