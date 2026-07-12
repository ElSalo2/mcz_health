"""Тесты главного меню и клавиатур."""

from app.bot.keyboards.builders import main_menu_keyboard


def test_main_menu_keyboard_is_persistent() -> None:
    keyboard = main_menu_keyboard(is_admin=True)
    assert keyboard.is_persistent is True
    assert keyboard.resize_keyboard is True
    assert len(keyboard.keyboard) == 3
