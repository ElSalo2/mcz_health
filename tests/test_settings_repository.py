"""Тесты репозитория настроек."""

import pytest

from app.infrastructure.database.unit_of_work import UnitOfWork


@pytest.mark.asyncio
async def test_settings_set_get_delete(uow: UnitOfWork) -> None:
    await uow.settings.set("last_manual_check", "2026-07-10")
    value = await uow.settings.get("last_manual_check")
    assert value == "2026-07-10"

    all_settings = await uow.settings.get_all()
    assert all_settings["last_manual_check"] == "2026-07-10"

    await uow.settings.delete("last_manual_check")
    assert await uow.settings.get("last_manual_check") is None


@pytest.mark.asyncio
async def test_settings_update(uow: UnitOfWork) -> None:
    await uow.settings.set("mode", "FAST")
    await uow.settings.set("mode", "FULL")
    assert await uow.settings.get("mode") == "FULL"
