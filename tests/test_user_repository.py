"""Тесты репозитория пользователей."""

import pytest

from app.core.exceptions import DatabaseError
from app.domain.entities.user import User
from app.domain.enums import UserStatus
from app.infrastructure.database.unit_of_work import UnitOfWork


@pytest.mark.asyncio
async def test_create_and_get_user(uow: UnitOfWork, sample_user: User) -> None:
    created = await uow.users.create(sample_user)
    assert created.id is not None
    assert created.phone == "+79001234567"

    by_phone = await uow.users.get_by_phone("79001234567")
    by_telegram = await uow.users.get_by_telegram_id(123456789)
    by_id = await uow.users.get_by_id(created.id)

    assert by_phone is not None
    assert by_telegram is not None
    assert by_id is not None
    assert by_phone.first_name == "Иван"


@pytest.mark.asyncio
async def test_create_duplicate_phone_raises(uow: UnitOfWork, sample_user: User) -> None:
    await uow.users.create(sample_user)
    duplicate = User(
        id=None,
        phone="+79001234567",
        telegram_id=999,
        first_name="Другой",
        last_name=None,
        username=None,
        status=UserStatus.ACTIVE,
    )
    with pytest.raises(DatabaseError, match="уже существует"):
        await uow.users.create(duplicate)


@pytest.mark.asyncio
async def test_update_user_status(uow: UnitOfWork, sample_user: User) -> None:
    created = await uow.users.create(sample_user)
    created.status = UserStatus.BLOCKED
    updated = await uow.users.update(created)
    assert updated.status == UserStatus.BLOCKED


@pytest.mark.asyncio
async def test_list_active_users(uow: UnitOfWork, sample_user: User) -> None:
    await uow.users.create(sample_user)

    blocked = User(
        id=None,
        phone="+79007654321",
        telegram_id=111,
        first_name="Блок",
        last_name=None,
        username=None,
        status=UserStatus.BLOCKED,
    )
    await uow.users.create(blocked)

    active = await uow.users.list_active()
    assert len(active) == 1
    assert active[0].telegram_id == 123456789


@pytest.mark.asyncio
async def test_delete_user(uow: UnitOfWork, sample_user: User) -> None:
    created = await uow.users.create(sample_user)
    await uow.users.delete(created.id)
    assert await uow.users.get_by_id(created.id) is None


@pytest.mark.asyncio
async def test_log_authorization(uow: UnitOfWork) -> None:
    await uow.users.log_authorization(
        telegram_id=555,
        phone="79001112233",
        success=False,
        reason="not_in_whitelist",
    )
