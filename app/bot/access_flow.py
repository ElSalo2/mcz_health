"""Единый сценарий отказа и отзыва доступа в Telegram."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from app.bot.keyboards.builders import (
    admin_contact_keyboard,
    contact_keyboard,
    hide_reply_keyboard,
    main_menu_keyboard,
)
from app.core.config import Settings
from app.locales.ru import Messages

logger = logging.getLogger(__name__)


def access_denied_text(config: Settings) -> str:
    return Messages.AUTH_ACCESS_DENIED.format(admin_contact=config.admin_contact_html)


def user_blocked_text(config: Settings) -> str:
    return Messages.AUTH_USER_BLOCKED.format(admin_contact=config.admin_contact_html)


def access_revoked_text(config: Settings) -> str:
    return Messages.AUTH_ACCESS_REVOKED.format(admin_contact=config.admin_contact_html)


async def send_admin_contact_card(bot: Bot, chat_id: int, config: Settings) -> bool:
    """Отправляет карточку контакта администратора (ваш профиль, не заявителя)."""
    phone = config.admin_contact_phone_normalized
    if phone is None:
        return False

    try:
        await bot.send_contact(
            chat_id=chat_id,
            phone_number=phone,
            first_name=config.admin_contact_first_name,
            last_name=config.admin_contact_last_name or "",
        )
        return True
    except TelegramAPIError as exc:
        logger.warning("Не удалось отправить карточку контакта администратора: %s", exc)
        return False


async def send_access_restricted(
    bot: Bot,
    chat_id: int,
    config: Settings,
    *,
    blocked: bool = False,
    revoked: bool = False,
) -> None:
    """Отправляет пользователю экран ограничения доступа и убирает меню."""
    if revoked:
        text = access_revoked_text(config)
    elif blocked:
        text = user_blocked_text(config)
    else:
        text = access_denied_text(config)

    await bot.send_message(chat_id=chat_id, text=text, reply_markup=hide_reply_keyboard())
    await send_admin_contact_card(bot, chat_id, config)
    await bot.send_message(
        chat_id=chat_id,
        text=Messages.ACCESS_DENIED_ACTION,
        reply_markup=admin_contact_keyboard(
            config.admin_telegram_url,
            config.admin_telegram_handle,
        ),
    )


async def send_auth_request(bot: Bot, chat_id: int) -> None:
    """Просит неавторизованного пользователя подтвердить телефон."""
    await bot.send_message(
        chat_id=chat_id,
        text=Messages.AUTH_REQUEST_CONTACT,
        reply_markup=contact_keyboard(),
    )


async def send_main_menu(bot: Bot, chat_id: int, *, is_admin: bool) -> None:
    """Восстанавливает главное меню после выдачи доступа."""
    await bot.send_message(
        chat_id=chat_id,
        text=Messages.WELCOME,
        reply_markup=main_menu_keyboard(is_admin=is_admin),
    )


async def reply_access_denied(message: Message, config: Settings, *, blocked: bool) -> None:
    """Ответ в чат при отказе в авторизации по контакту."""
    await send_access_restricted(
        message.bot,
        message.chat.id,
        config,
        blocked=blocked,
        revoked=False,
    )


async def reply_unauthorized(
    message: Message,
    config: Settings,
    *,
    blocked: bool,
    revoked: bool,
) -> None:
    """Ответ в чат при попытке использовать защищённые функции без доступа."""
    if revoked or blocked:
        await send_access_restricted(
            message.bot,
            message.chat.id,
            config,
            blocked=blocked,
            revoked=revoked,
        )
        return

    await send_auth_request(message.bot, message.chat.id)
