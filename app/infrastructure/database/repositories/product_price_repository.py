"""Репозиторий снимков цен товаров."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import ProductPriceSnapshotModel
from app.infrastructure.database.utils import utc_now
from app.services.monitoring.price_validator import format_price_value, parse_price_value


class ProductPriceRepository:
    """Хранит последние известные цены товаров для сравнения между проверками."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(self) -> dict[str, Decimal]:
        """Возвращает все сохранённые цены по offer_id."""
        result = await self._session.execute(select(ProductPriceSnapshotModel))
        prices: dict[str, Decimal] = {}
        for model in result.scalars():
            parsed = parse_price_value(model.price)
            if parsed is not None:
                prices[model.offer_id] = parsed
        return prices

    async def upsert_many(
        self,
        prices: dict[str, Decimal],
        *,
        updated_at: datetime | None = None,
    ) -> None:
        """Сохраняет или обновляет цены товаров."""
        if not prices:
            return

        timestamp = updated_at or utc_now()
        offer_ids = list(prices.keys())
        result = await self._session.execute(
            select(ProductPriceSnapshotModel).where(
                ProductPriceSnapshotModel.offer_id.in_(offer_ids)
            )
        )
        existing = {model.offer_id: model for model in result.scalars()}

        for offer_id, price in prices.items():
            price_text = format_price_value(price)
            model = existing.get(offer_id)
            if model is None:
                self._session.add(
                    ProductPriceSnapshotModel(
                        offer_id=offer_id,
                        price=price_text,
                        updated_at=timestamp,
                    )
                )
            else:
                model.price = price_text
                model.updated_at = timestamp

        await self._session.flush()
