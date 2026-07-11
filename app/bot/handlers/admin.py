"""Административные обработчики."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.builders import (
    ADMIN_ADD,
    ADMIN_CANCEL,
    ADMIN_REFRESH,
    admin_cancel_keyboard,
    admin_panel_keyboard,
)
from app.bot.states.admin import AdminStates
from app.core.config import Settings
from app.core.exceptions import AppError, DatabaseError, NotificationError
from app.locales.ru import Messages
from app.services.admin_panel_service import AdminPanelService
from app.services.notification_service import NotificationService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router(name="admin")


@router.message(lambda m: m.text == Messages.BTN_USERS)
async def manage_users(
    message: Message,
    admin_panel_service: AdminPanelService,
    user_service: UserService,
) -> None:
    """Показывает список пользователей и панель управления."""
    users = await user_service.list_users()
    text = await admin_panel_service.format_users_list()
    await message.answer(text, reply_markup=admin_panel_keyboard(users))


@router.callback_query(F.data == ADMIN_REFRESH)
async def refresh_users(
    callback: CallbackQuery,
    admin_panel_service: AdminPanelService,
    user_service: UserService,
) -> None:
    """Обновляет список пользователей."""
    users = await user_service.list_users()
    text = await admin_panel_service.format_users_list()
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=admin_panel_keyboard(users))
    await callback.answer()


@router.callback_query(F.data == ADMIN_ADD)
async def start_add_user(callback: CallbackQuery, state: FSMContext) -> None:
    """Начинает добавление пользователя."""
    await state.set_state(AdminStates.waiting_phone)
    if callback.message is not None:
        await callback.message.answer(Messages.ADMIN_ENTER_PHONE, reply_markup=admin_cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data == ADMIN_CANCEL)
async def cancel_admin_action(callback: CallbackQuery, state: FSMContext) -> None:
    """Отменяет текущее административное действие."""
    await state.clear()
    if callback.message is not None:
        await callback.message.answer("Действие отменено.")
    await callback.answer()


@router.message(AdminStates.waiting_phone)
async def process_add_user_phone(
    message: Message,
    state: FSMContext,
    admin_panel_service: AdminPanelService,
    user_service: UserService,
) -> None:
    """Добавляет пользователя по введённому номеру."""
    if message.text is None:
        await message.answer(Messages.ADMIN_INVALID_PHONE)
        return

    try:
        user = await admin_panel_service.add_user_by_phone(message.text)
        await state.clear()
        await message.answer(AdminPanelService.format_user_action_message(user, action="added"))
        users = await user_service.list_users()
        text = await admin_panel_service.format_users_list()
        await message.answer(text, reply_markup=admin_panel_keyboard(users))
    except (DatabaseError, ValueError):
        await message.answer(Messages.ADMIN_INVALID_PHONE)
    except AppError:
        logger.exception("Ошибка добавления пользователя")
        await message.answer(Messages.INTERNAL_ERROR)


@router.callback_query(F.data.startswith("admin:delete:"))
async def delete_user_callback(
    callback: CallbackQuery,
    admin_panel_service: AdminPanelService,
    user_service: UserService,
    notification_service: NotificationService,
) -> None:
    """Удаляет пользователя."""
    user_id = int(callback.data.split(":")[-1])
    user = await admin_panel_service.get_user(user_id)
    if user is None:
        await callback.answer(Messages.ADMIN_USER_NOT_FOUND, show_alert=True)
        return

    telegram_id = user.telegram_id
    await admin_panel_service.delete_user(user_id)
    await callback.answer(AdminPanelService.format_user_action_message(user, action="deleted"))

    if telegram_id:
        try:
            await notification_service.revoke_user_access(telegram_id, revoked=True)
        except NotificationError:
            logger.exception(
                "Не удалось уведомить пользователя об удалении: telegram_id=%s",
                telegram_id,
            )

    users = await user_service.list_users()
    text = await admin_panel_service.format_users_list()
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=admin_panel_keyboard(users))


@router.callback_query(F.data.startswith("admin:toggle:"))
async def toggle_user_block_callback(
    callback: CallbackQuery,
    config: Settings,
    admin_panel_service: AdminPanelService,
    user_service: UserService,
    notification_service: NotificationService,
) -> None:
    """Блокирует или разблокирует пользователя."""
    user_id = int(callback.data.split(":")[-1])
    try:
        user = await admin_panel_service.toggle_block(user_id)
    except ValueError:
        await callback.answer(Messages.ADMIN_USER_NOT_FOUND, show_alert=True)
        return

    action = "unblocked" if user.is_active else "blocked"
    await callback.answer(AdminPanelService.format_user_action_message(user, action=action))

    if user.telegram_id:
        try:
            if user.is_active:
                await notification_service.restore_user_access(
                    user.telegram_id,
                    is_admin=user.telegram_id == config.admin_id,
                )
            else:
                await notification_service.revoke_user_access(
                    user.telegram_id,
                    blocked=True,
                    revoked=False,
                )
        except NotificationError:
            logger.exception(
                "Не удалось обновить доступ пользователя: telegram_id=%s",
                user.telegram_id,
            )

    users = await user_service.list_users()
    text = await admin_panel_service.format_users_list()
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=admin_panel_keyboard(users))
