"""Тесты доменного слоя."""

from app.domain.value_objects.coordinates import Coordinates


def test_coordinates_valid() -> None:
    coords = Coordinates(latitude=55.75, longitude=37.62)
    assert coords.is_valid() is True


def test_coordinates_invalid_latitude() -> None:
    coords = Coordinates(latitude=91.0, longitude=37.62)
    assert coords.is_valid() is False


def test_coordinates_invalid_longitude() -> None:
    coords = Coordinates(latitude=55.75, longitude=181.0)
    assert coords.is_valid() is False
