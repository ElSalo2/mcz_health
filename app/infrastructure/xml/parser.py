"""Парсер XML с использованием lxml."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from lxml import etree

from app.core.exceptions import FeedParseError
from app.domain.enums import FeedType
from app.infrastructure.xml.dates import parse_product_feed_date


@dataclass(slots=True)
class ParsedFeed:
    """Результат парсинга XML."""

    root: etree._Element
    feed_date: datetime | None
    raw_date: str | None


PRODUCT_ROOT_TAG = "yml_catalog"
STORE_ROOT_TAG = "companies"


class XmlParser:
    """Парсит и валидирует структуру XML-фидов."""

    def parse(self, content: bytes, feed_type: str) -> ParsedFeed:
        """Парсит XML и извлекает метаданные."""
        try:
            root = etree.fromstring(content)
        except etree.XMLSyntaxError as exc:
            raise FeedParseError(f"Некорректный XML: {exc}") from exc

        raw_date: str | None = None
        feed_date: datetime | None = None

        if feed_type == FeedType.PRODUCT.value:
            raw_date = root.get("date")
            feed_date = parse_product_feed_date(raw_date)
        elif feed_type == FeedType.STORE.value:
            raw_date = None
            feed_date = None

        return ParsedFeed(root=root, feed_date=feed_date, raw_date=raw_date)

    def validate_structure(self, parsed: ParsedFeed, feed_type: str) -> None:
        """Проверяет структуру XML на соответствие ожидаемой схеме."""
        root_tag = etree.QName(parsed.root).localname

        if feed_type == FeedType.PRODUCT.value:
            if root_tag != PRODUCT_ROOT_TAG:
                raise FeedParseError(f"Ожидался корневой элемент {PRODUCT_ROOT_TAG}, получен {root_tag}")
            shop = parsed.root.find("shop")
            if shop is None:
                raise FeedParseError("Отсутствует элемент shop")
            offers = shop.find("offers")
            if offers is None:
                raise FeedParseError("Отсутствует элемент offers")
            return

        if feed_type == FeedType.STORE.value:
            if root_tag != STORE_ROOT_TAG:
                raise FeedParseError(f"Ожидался корневой элемент {STORE_ROOT_TAG}, получен {root_tag}")
            if not parsed.root.findall("company"):
                raise FeedParseError("Фид магазинов не содержит элементов company")
            return

        raise FeedParseError(f"Неизвестный тип фида: {feed_type}")

