"""Географические координаты."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Coordinates:
    """Широта и долгота точки на карте."""

    latitude: float
    longitude: float

    def is_valid(self) -> bool:
        """Проверяет корректность координат."""
        return -90.0 <= self.latitude <= 90.0 and -180.0 <= self.longitude <= 180.0
