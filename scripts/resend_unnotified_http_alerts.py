"""Отправляет в Telegram все неуведомлённые HTTP-ошибки из active_errors."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import load_settings
from app.core.logging import setup_logging
from app.domain.entities.issue import Issue
from app.domain.enums import FeedType, IssueCategory, Severity
from app.infrastructure.database.manager import DatabaseManager
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.services.monitoring.alert_policy import should_alert_issue
from app.services.monitoring.live_issue_reporter import IMMEDIATE_HTTP_ALERT_KEYS
from app.services.notification_service import NotificationService
from app.bot.tracking_bot import TrackingBot
from app.services.bot_message_tracker import BotMessageTracker

logger = logging.getLogger(__name__)


def _active_error_to_issue(active_error) -> Issue:
    context = dict(active_error.context_json)
    message_key = str(context.get("message_key") or "")
    return Issue(
        fingerprint=active_error.fingerprint,
        severity=active_error.severity,
        category=active_error.category,
        feed_type=active_error.feed_type,
        message_key=message_key,
        context=context,
        object_id=str(context.get("id") or context.get("offer_id") or "") or None,
        object_name=str(context.get("name") or "") or None,
    )


async def main() -> None:
    settings = load_settings()
    setup_logging(settings.log_level, settings.logs_dir)
    db = DatabaseManager(settings)
    await db.startup()

    tracker = BotMessageTracker(db.session_factory)
    bot = TrackingBot(settings=settings, tracker=tracker, session_factory=db.session_factory)
    notification_service = NotificationService(
        bot,
        settings,
        session_factory=db.session_factory,
    )

    pending: list[Issue] = []
    async with UnitOfWork(db.session_factory) as uow:
        for feed_type in (FeedType.STORE, FeedType.PRODUCT):
            for active_error in await uow.errors.get_active_errors(feed_type):
                if active_error.notified:
                    continue
                issue = _active_error_to_issue(active_error)
                if issue.message_key not in IMMEDIATE_HTTP_ALERT_KEYS:
                    continue
                if not should_alert_issue(issue):
                    continue
                pending.append(issue)

    if not pending:
        print("Нет неуведомлённых HTTP-ошибок в active_errors.")
        await bot.session.close()
        await db.shutdown()
        return

    print(f"Отправка {len(pending)} HTTP-алертов...")
    await notification_service.notify_new_issues(pending)
    print("Готово.")

    await bot.session.close()
    await db.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
