"""Обработка заявок на доступ от администратора."""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards.builders import (
    ACCESS_APPROVE_PREFIX,
    ACCESS_REJECT_PREFIX,
    main_menu_keyboard,
)
from app.core.config import Settings
from app.core.exceptions import AppError, DatabaseError
from app.infrastructure.database.utils import normalize_phone
from app.locales.ru import Messages
from app.services.notification_service import NotificationService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router(name="access_request")


def _is_admin(callback: CallbackQuery, settings: Settings) -> bool:
    return callback.from_user is not None and callback.from_user.id == settings.admin_id


def _parse_approve_callback(data: str) -> tuple[int, str]:
    payload = data.removeprefix(ACCESS_APPROVE_PREFIX)
    telegram_id_str, phone_token = payload.split(":", maxsplit=1)
    return int(telegram_id_str), f"+{phone_token}"


def _parse_reject_callback(data: str) -> int:
    return int(data.removeprefix(ACCESS_REJECT_PREFIX))


@router.callback_query(F.data.startswith(ACCESS_APPROVE_PREFIX))
async def approve_access_request(
    callback: CallbackQuery,
    bot: Bot,
    config: Settings,
    user_service: UserService,
    notification_service: NotificationService,
) -> None:
    """Добавляет пользователя по заявке администратора."""
    if not _is_admin(callback, config):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    if callback.data is None:
        await callback.answer()
        return

    try:
        telegram_id, phone = _parse_approve_callback(callback.data)
        normalized_phone = normalize_phone(phone)
    except (ValueError, IndexError):
        await callback.answer("Некорректные данные заявки", show_alert=True)
        return

    if await user_service.is_authorized(telegram_id):
        await callback.answer(Messages.ACCESS_REQUEST_ALREADY_AUTHORIZED, show_alert=True)
        if callback.message is not None:
            await callback.message.edit_reply_markup(reply_markup=None)
        return

    try:
        chat = await bot.get_chat(telegram_id)
        user = await user_service.approve_access_request(
            phone=normalized_phone,
            telegram_id=telegram_id,
            first_name=chat.first_name,
            last_name=chat.last_name,
            username=chat.username,
        )
    except (DatabaseError, ValueError, AppError):
        logger.exception("Ошибка одобрения заявки на доступ: telegram_id=%s", telegram_id)
        await callback.answer(Messages.INTERNAL_ERROR, show_alert=True)
        return

    await notification_service.notify_user(telegram_id, Messages.AUTH_ACCESS_GRANTED)
    is_admin = telegram_id == config.admin_id
    await bot.send_message(
        chat_id=telegram_id,
        text=Messages.WELCOME,
        reply_markup=main_menu_keyboard(is_admin=is_admin),
    )

    if callback.message is not None:
        handled_text = (
            f"{callback.message.text}\n\n"
            f"{Messages.ACCESS_REQUEST_HANDLED_APPROVE.format(phone=user.phone)}"
        )
        await callback.message.edit_text(handled_text, reply_markup=None)

    await callback.answer(Messages.ACCESS_REQUEST_HANDLED_APPROVE.format(phone=user.phone))


@router.callback_query(F.data.startswith(ACCESS_REJECT_PREFIX))
async def reject_access_request(
    callback: CallbackQuery,
    config: Settings,
    notification_service: NotificationService,
) -> None:
    """Отклоняет заявку на доступ."""
    if not _is_admin(callback, config):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    if callback.data is None:
        await callback.answer()
        return

    try:
        telegram_id = _parse_reject_callback(callback.data)
    except ValueError:
        await callback.answer("Некорректные данные заявки", show_alert=True)
        return

    try:
        await notification_service.notify_user(telegram_id, Messages.AUTH_ACCESS_REJECTED)
    except AppError:
        logger.exception("Ошибка уведомления об отказе: telegram_id=%s", telegram_id)

    if callback.message is not None:
        handled_text = f"{callback.message.text}\n\n{Messages.ACCESS_REQUEST_HANDLED_REJECT}"
        await callback.message.edit_text(handled_text, reply_markup=None)

    await callback.answer(Messages.ACCESS_REQUEST_HANDLED_REJECT)
