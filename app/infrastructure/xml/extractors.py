"""Извлечение сущностей из XML-фидов."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from lxml import etree

from app.infrastructure.xml.dates import parse_outlet_date, parse_product_feed_date


@dataclass(slots=True)
class StoreItem:
    """Магазин из XML-фида."""

    company_id: str
    name: str
    address: str
    working_time: str
    country: str
    latitude: float | None
    longitude: float | None
    url: str
    info_page: str
    actualization_date: str | None
    actualization_datetime: datetime | None
    photos: list[str]
    gallery_url: str | None
    social_links: list[str]
    raw: dict[str, Any]


@dataclass(slots=True)
class CategoryItem:
    """Категория из XML-фида товаров."""

    category_id: str
    name: str
    parent_id: str | None


@dataclass(slots=True)
class ProductItem:
    """Товар из XML-фида."""

    offer_id: str
    name: str
    name_source: str | None
    vendor: str
    price: str
    price_source: str | None
    oldprice_source: str | None
    url: str
    url_source: str | None
    available_source: str | None
    stock_source: str | None
    pictures: list[str]
    category_id: str
    raw: dict[str, Any]


def resolve_store_feed_date(stores: list[StoreItem]) -> datetime | None:
    """Возвращает самую свежую actualization-date среди магазинов."""
    dates = [store.actualization_datetime for store in stores if store.actualization_datetime]
    return max(dates) if dates else None


class FeedExtractor:
    """Извлекает магазины и товары из распарсенного XML."""

    def extract_stores(self, root: etree._Element) -> list[StoreItem]:
        """Извлекает список магазинов."""
        stores: list[StoreItem] = []
        for company in root.findall("company"):
            company_id = _text(company.find("company-id"))
            actualization_date = _text(company.find("actualization-date"))
            photos_block = company.find("photos")
            photos = [
                photo.get("url", "").strip()
                for photo in (photos_block.findall("photo") if photos_block is not None else [])
                if photo.get("url")
            ]
            stores.append(
                StoreItem(
                    company_id=company_id,
                    name=_localized_text(company, "name"),
                    address=_localized_text(company, "address"),
                    working_time=_localized_text(company, "working-time"),
                    country=_localized_text(company, "country"),
                    latitude=_parse_float(_text(company.find("coordinates/lat"))),
                    longitude=_parse_float(_text(company.find("coordinates/lon"))),
                    url=_text(company.find("url")),
                    info_page=_text(company.find("info-page")),
                    actualization_date=actualization_date or None,
                    actualization_datetime=parse_outlet_date(actualization_date),
                    photos=photos,
                    gallery_url=photos_block.get("gallery-url") if photos_block is not None else None,
                    social_links=[_text(node) for node in company.findall("add-url") if _text(node)],
                    raw={},
                )
            )
        return stores

    def extract_categories(self, root: etree._Element) -> list[CategoryItem]:
        """Извлекает дерево категорий из shop/categories."""
        categories_parent = root.find("shop/categories")
        if categories_parent is None:
            return []

        categories: list[CategoryItem] = []
        for node in categories_parent.findall("category"):
            category_id = (node.get("id") or "").strip()
            parent_id = (node.get("parentId") or "").strip() or None
            categories.append(
                CategoryItem(
                    category_id=category_id,
                    name=_text(node) or category_id,
                    parent_id=parent_id,
                )
            )
        return categories

    def extract_products(self, root: etree._Element) -> list[ProductItem]:
        """Извлекает список товаров."""
        offers_parent = root.find("shop/offers")
        if offers_parent is None:
            return []

        products: list[ProductItem] = []
        for offer in offers_parent.findall("offer"):
            offer_id = offer.get("id", "").strip()
            name_node = offer.find("name")
            name_source = None if name_node is None else (name_node.text if name_node.text is not None else "")
            price_node = offer.find("price")
            price_source = None if price_node is None else (price_node.text if price_node.text is not None else "")
            oldprice_node = offer.find("oldprice")
            oldprice_source = (
                None if oldprice_node is None else (oldprice_node.text if oldprice_node.text is not None else "")
            )
            url_node = offer.find("url")
            url_source = None if url_node is None else (url_node.text if url_node.text is not None else "")
            stock_node = offer.find("count")
            stock_source = None if stock_node is None else (stock_node.text if stock_node.text is not None else "")
            available_attr = offer.get("available")
            available_source = None if available_attr is None else available_attr.strip()
            products.append(
                ProductItem(
                    offer_id=offer_id,
                    name=name_source.strip() if name_source is not None else "",
                    name_source=name_source,
                    vendor=_text(offer.find("vendor")),
                    price=_text(offer.find("price")),
                    price_source=price_source,
                    oldprice_source=oldprice_source,
                    url=_text(offer.find("url")),
                    url_source=url_source,
                    available_source=available_source,
                    stock_source=stock_source,
                    pictures=[_text(node) for node in offer.findall("picture") if _text(node)],
                    category_id=_text(offer.find("categoryId")),
                    raw={},
                )
            )
        return products


def _text(node: etree._Element | None) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _localized_text(parent: etree._Element, tag: str) -> str:
    nodes = parent.findall(tag)
    for node in nodes:
        if node.get("lang") == "ru" and node.text:
            return node.text.strip()
    for node in nodes:
        if node.text:
            return node.text.strip()
    return ""


def _parse_float(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
