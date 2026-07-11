"""Обработчик /start и авторизации по контакту."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.builders import (
    admin_contact_keyboard,
    contact_keyboard,
    hide_reply_keyboard,
    main_menu_keyboard,
)
from app.core.config import Settings
from app.core.exceptions import AppError
from app.locales.ru import Messages
from app.services.auth_service import AuthService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router(name="start")


def _access_denied_message(config: Settings) -> str:
    return Messages.AUTH_ACCESS_DENIED.format(admin_contact=config.admin_contact_html)


def _user_blocked_message(config: Settings) -> str:
    return Messages.AUTH_USER_BLOCKED.format(admin_contact=config.admin_contact_html)


async def _reply_access_denied(message: Message, config: Settings, *, blocked: bool) -> None:
    text = _user_blocked_message(config) if blocked else _access_denied_message(config)
    await message.answer(text, reply_markup=hide_reply_keyboard())
    await message.answer(
        Messages.ACCESS_DENIED_ACTION,
        reply_markup=admin_contact_keyboard(
            config.admin_telegram_url,
            config.admin_telegram_handle,
        ),
    )


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
    config: Settings,
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
        await _reply_access_denied(message, config, blocked=result.user_blocked)
        return

    if result.success:
        is_admin = await user_service.is_admin(message.from_user.id)
        await message.answer(Messages.AUTH_SUCCESS)
        await message.answer(
            Messages.WELCOME,
            reply_markup=main_menu_keyboard(is_admin=is_admin),
        )
