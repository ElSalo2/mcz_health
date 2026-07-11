"""Единый сценарий отказа и отзыва доступа в Telegram."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import Message

from app.bot.keyboards.builders import contact_keyboard, hide_reply_keyboard, main_menu_keyboard
from app.bot.tracking_bot import TrackingBot
from app.core.config import Settings
from app.locales.ru import Messages

logger = logging.getLogger(__name__)


def access_denied_text() -> str:
    return Messages.AUTH_ACCESS_DENIED


def user_blocked_text() -> str:
    return Messages.AUTH_USER_BLOCKED


def access_revoked_text() -> str:
    return Messages.AUTH_ACCESS_REVOKED


async def _clear_chat_history(bot: Bot, chat_id: int) -> None:
    if isinstance(bot, TrackingBot):
        await bot.tracker.clear_chat(bot, chat_id)


async def send_access_restricted(
    bot: Bot,
    chat_id: int,
    config: Settings,
    *,
    blocked: bool = False,
    revoked: bool = False,
) -> None:
    """Отправляет пользователю экран ограничения доступа и убирает меню."""
    if not blocked and not revoked:
        await bot.send_message(
            chat_id=chat_id,
            text=access_denied_text(),
            reply_markup=hide_reply_keyboard(),
        )
        return

    await _clear_chat_history(bot, chat_id)
    text = access_revoked_text() if revoked else user_blocked_text()
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=hide_reply_keyboard())


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
