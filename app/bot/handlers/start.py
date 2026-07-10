"""Обработчик /start и авторизации по контакту."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.builders import contact_keyboard, main_menu_keyboard
from app.core.config import Settings
from app.core.exceptions import AppError
from app.locales.ru import Messages
from app.services.auth_service import AuthService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    user_service: UserService,
    config: Settings,
) -> None:
    """Обрабатывает команду /start."""
    if message.from_user is None:
        return

    telegram_id = message.from_user.id

    if await user_service.is_authorized(telegram_id):
        is_admin = await user_service.is_admin(telegram_id)
        await message.answer(
            Messages.WELCOME,
            reply_markup=main_menu_keyboard(is_admin=is_admin),
        )
        return

    await message.answer(
        Messages.AUTH_REQUEST_CONTACT,
        reply_markup=contact_keyboard(),
    )


@router.message(F.contact)
async def handle_contact(
    message: Message,
    auth_service: AuthService,
    user_service: UserService,
) -> None:
    """Обрабатывает отправку контакта для авторизации."""
    if message.from_user is None or message.contact is None:
        return

    try:
        result = await auth_service.authenticate_contact(message.from_user, message.contact)
    except AppError:
        logger.exception("Ошибка при авторизации пользователя %s", message.from_user.id)
        await message.answer(Messages.INTERNAL_ERROR, reply_markup=contact_keyboard())
        return

    if result.identity_failed:
        await message.answer(Messages.AUTH_IDENTITY_FAILED, reply_markup=contact_keyboard())
        return

    if result.access_denied:
        if result.user_blocked:
            await message.answer(Messages.AUTH_USER_BLOCKED, reply_markup=contact_keyboard())
        else:
            await message.answer(Messages.AUTH_ACCESS_DENIED, reply_markup=contact_keyboard())
        return

    if result.success:
        is_admin = await user_service.is_admin(message.from_user.id)
        await message.answer(Messages.AUTH_SUCCESS)
        await message.answer(
            Messages.WELCOME,
            reply_markup=main_menu_keyboard(is_admin=is_admin),
        )
