"""Обработчики просмотра результатов автоматических проверок."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import Message

from app.core.exceptions import AppError
from app.locales.ru import Messages
from app.services.check_query_service import CheckQueryService

logger = logging.getLogger(__name__)

router = Router(name="checks")


@router.message(lambda m: m.text == Messages.BTN_LAST_CHECK)
async def last_check(
    message: Message,
    check_query_service: CheckQueryService,
) -> None:
    """Показывает результат последней автоматической проверки."""
    try:
        report = await check_query_service.get_last_check_report()
        await message.answer(report)
    except AppError:
        logger.exception("Ошибка получения последней проверки")
        await message.answer(Messages.INTERNAL_ERROR)


@router.message(lambda m: m.text == Messages.BTN_HISTORY)
async def check_history(
    message: Message,
    check_query_service: CheckQueryService,
) -> None:
    """Показывает историю автоматических проверок."""
    try:
        report = await check_query_service.get_history_report(limit=10)
        await message.answer(report)
    except AppError:
        logger.exception("Ошибка получения истории проверок")
        await message.answer(Messages.INTERNAL_ERROR)
