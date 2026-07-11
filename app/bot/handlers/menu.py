"""Обработчик главного меню."""

from aiogram import Router
from aiogram.types import Message

from app.locales.ru import Messages

router = Router(name="menu")


@router.message(lambda m: m.text == Messages.BTN_ABOUT)
async def about_system(message: Message) -> None:
    """Показывает информацию о системе."""
    await message.answer(Messages.ABOUT_SYSTEM)

