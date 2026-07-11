"""Сервис отправки уведомлений в Telegram."""

from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup

from app.core.config import Settings
from app.core.error_handler import handle_service_errors
from app.core.exceptions import NotificationError
from app.domain.entities.issue import Issue
from app.locales.ru import Messages
from app.services.monitoring.alert_context import (
    enrich_alert_context,
    format_alert_template,
    truncate_alert_text,
)
from app.services.monitoring.alert_policy import CRITICAL_ALERT_KEYS, filter_alert_issues

logger = logging.getLogger(__name__)


class NotificationService:
    """Форматирует и отправляет уведомления пользователям."""

    def __init__(
        self,
        bot: Bot,
        settings: Settings,
        session_factory=None,
    ) -> None:
        self._bot = bot
        self._settings = settings
        self._session_factory = session_factory

    def format_alert(self, message_key: str, context: dict[str, Any], *, feed_type: str | None = None) -> str:
        """Форматирует Telegram-алерт по шаблону из локализации."""
        template = getattr(Messages, message_key, None)
        if template is None:
            raise ValueError(f"Неизвестный ключ сообщения: {message_key}")

        feed_url = None
        if message_key == "XML_UNAVAILABLE" and feed_type is not None:
            feed_url = self._settings.get_feed_url(feed_type)

        enriched = enrich_alert_context(
            message_key,
            context,
            feed_url=feed_url,
            min_price_threshold=self._settings.min_product_price_warning,
        )
        text = format_alert_template(template, enriched)
        return truncate_alert_text(text)

    def format_message(self, message_key: str, context: dict[str, Any]) -> str:
        """Форматирует шаблон сообщения из локализации."""
        return self.format_alert(message_key, context)

    @handle_service_errors
    async def notify_user(self, telegram_id: int, text: str) -> None:
        """Отправляет сообщение одному пользователю."""
        try:
            await self._bot.send_message(chat_id=telegram_id, text=text)
            logger.debug("Уведомление отправлено пользователю %s", telegram_id)
        except TelegramAPIError as exc:
            logger.error("Ошибка отправки уведомления пользователю %s: %s", telegram_id, exc)
            raise NotificationError(
                "Не удалось отправить уведомление пользователю",
                details={"telegram_id": telegram_id, "error": str(exc)},
            ) from exc

    @handle_service_errors
    async def notify_all_active_users(self, text: str) -> None:
        """Отправляет сообщение всем активным пользователям."""
        if self._session_factory is None:
            raise NotificationError("Session factory не настроен для массовых уведомлений")

        from app.infrastructure.database.unit_of_work import UnitOfWork

        async with UnitOfWork(self._session_factory) as uow:
            users = await uow.users.list_active()

        for user in users:
            if user.telegram_id:
                await self.notify_user(user.telegram_id, text)

    @handle_service_errors
    async def notify_admin(
        self,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        """Отправляет сообщение администратору."""
        try:
            await self._bot.send_message(
                chat_id=self._settings.admin_id,
                text=text,
                reply_markup=reply_markup,
            )
            logger.info("Уведомление отправлено администратору")
        except TelegramAPIError as exc:
            logger.error("Ошибка отправки уведомления администратору: %s", exc)
            raise NotificationError(
                "Не удалось отправить уведомление администратору",
                details={"admin_id": self._settings.admin_id, "error": str(exc)},
            ) from exc

    @handle_service_errors
    async def notify_new_issues(self, issues: list[Issue]) -> None:
        """Отправляет уведомления о новых проблемах согласно политике алертов."""
        alert_issues = filter_alert_issues(issues)
        if not alert_issues:
            return
        for issue in alert_issues:
            text = self.format_alert(
                issue.message_key,
                issue.context,
                feed_type=issue.feed_type.value,
            )
            await self.notify_all_active_users(text)
            if self._session_factory is not None:
                from app.infrastructure.database.unit_of_work import UnitOfWork

                async with UnitOfWork(self._session_factory) as uow:
                    await uow.errors.mark_notified(issue.fingerprint)

    @handle_service_errors
    async def notify_resolved_issues(self, issues: list[Issue]) -> None:
        """Отправляет уведомления об устранении ранее отправленных critical-алертов."""
        for issue in issues:
            if issue.message_key != "ISSUE_RESOLVED":
                continue
            if not issue.context.get("notified"):
                continue
            original_key = str(issue.context.get("error_code") or issue.context.get("message_key") or "")
            if original_key not in CRITICAL_ALERT_KEYS:
                continue
            text = self.format_alert("ISSUE_RESOLVED", issue.context)
            await self.notify_all_active_users(text)
