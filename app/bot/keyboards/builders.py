"""Построители клавиатур."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.domain.entities.user import User
from app.domain.enums import UserStatus
from app.locales.ru import Messages

ADMIN_REFRESH = "admin:refresh"
ADMIN_ADD = "admin:add"
ADMIN_CANCEL = "admin:cancel"
ADMIN_BACK = "admin:back"
ACCESS_APPROVE_PREFIX = "access:approve:"
ACCESS_REJECT_PREFIX = "access:reject:"


def contact_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отправки контакта."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=Messages.BTN_SHARE_CONTACT, request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Главное меню пользователя (только просмотр, без ручного запуска проверок)."""
    rows = [
        [KeyboardButton(text=Messages.BTN_LAST_CHECK), KeyboardButton(text=Messages.BTN_HISTORY)],
        [KeyboardButton(text=Messages.BTN_ABOUT)],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=Messages.BTN_USERS)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def admin_panel_keyboard(users: list[User]) -> InlineKeyboardMarkup:
    """Клавиатура управления пользователями."""
    rows: list[list[InlineKeyboardButton]] = []

    for user in users:
        if user.id is None:
            continue
        action_label = "🔓 Разблок." if user.status == UserStatus.BLOCKED else "🔒 Блок."
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{action_label} {user.phone}",
                    callback_data=f"admin:toggle:{user.id}",
                ),
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"admin:delete:{user.id}",
                ),
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(text=Messages.BTN_ADMIN_ADD, callback_data=ADMIN_ADD),
            InlineKeyboardButton(text=Messages.BTN_ADMIN_REFRESH, callback_data=ADMIN_REFRESH),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены ввода."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=Messages.BTN_CANCEL, callback_data=ADMIN_CANCEL)],
        ]
    )


def _phone_callback_token(phone: str) -> str:
    """Кодирует телефон для callback_data (только цифры, без +)."""
    return "".join(ch for ch in phone if ch.isdigit())


def access_request_keyboard(telegram_id: int, phone: str) -> InlineKeyboardMarkup:
    """Клавиатура заявки на доступ для администратора."""
    phone_token = _phone_callback_token(phone)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=Messages.BTN_ACCESS_APPROVE,
                    callback_data=f"{ACCESS_APPROVE_PREFIX}{telegram_id}:{phone_token}",
                ),
                InlineKeyboardButton(
                    text=Messages.BTN_ACCESS_REJECT,
                    callback_data=f"{ACCESS_REJECT_PREFIX}{telegram_id}",
                ),
            ]
        ]
    )
