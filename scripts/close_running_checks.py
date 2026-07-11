"""Закрывает зависшие проверки со статусом running."""

from __future__ import annotations

import asyncio

from app.core.config import load_settings
from app.domain.entities.feed_check import FeedCheck
from app.domain.enums import CheckStatus
from app.infrastructure.database.manager import DatabaseManager
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.infrastructure.database.utils import utc_now


async def main() -> None:
    settings = load_settings()
    db = DatabaseManager(settings)
    await db.startup()
    finished_at = utc_now()
    async with UnitOfWork(db.session_factory) as uow:
        running = await uow.checks.list_running()
        for check in running:
            started_at = check.started_at
            if started_at is not None and started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=finished_at.tzinfo)
            duration = (finished_at - started_at).total_seconds() if started_at else None
            await uow.checks.update(
                FeedCheck(
                    id=check.id,
                    feed_type=check.feed_type,
                    status=CheckStatus.INTERRUPTED,
                    started_at=check.started_at,
                    finished_at=finished_at,
                    duration_seconds=duration,
                    item_count=check.item_count,
                    sha256=check.sha256,
                    content_size=None,
                    feed_date=check.feed_date,
                    critical_count=check.critical_count,
                    warning_count=check.warning_count,
                    triggered_by=check.triggered_by,
                )
            )
        print(f"Closed running checks: {len(running)}")
    await db.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
