"""Статистика выполненной или выполняющейся проверки фида."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class CheckStats:
    """Счётчики проверенных параметров каталога."""

    items_in_feed: int = 0
    categories_in_feed: int = 0
    categories_used_by_products: int = 0

    product_pages_planned: int = 0
    product_pages_checked: int = 0
    product_pages_ok: int = 0

    product_images_planned: int = 0
    product_images_checked: int = 0
    product_images_ok: int = 0

    store_pages_planned: int = 0
    store_pages_checked: int = 0
    store_pages_ok: int = 0

    store_images_planned: int = 0
    store_images_checked: int = 0
    store_images_ok: int = 0

    prices_checked: int = 0
    stocks_checked: int = 0
    names_checked: int = 0
    required_fields_checked: int = 0
    categories_validated: int = 0

    http_total_planned: int = 0
    http_total_checked: int = 0
    http_total_ok: int = 0

    warnings_by_type: dict[str, int] = field(default_factory=dict)
    critical_by_type: dict[str, int] = field(default_factory=dict)

    skip_http: bool = False

    max_duration_seconds: int = 0
    http_slot_seconds: float = 0.0
    planned_duration_seconds: float = 0.0

    extra: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> CheckStats:
        if not data:
            return cls()
        known = {field.name for field in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        values = {key: data[key] for key in known if key in data}
        if "extra" in data and isinstance(data["extra"], dict):
            values["extra"] = data["extra"]
        for key in ("warnings_by_type", "critical_by_type"):
            if key in data and isinstance(data[key], dict):
                values[key] = {str(k): int(v) for k, v in data[key].items()}
        return cls(**values)
