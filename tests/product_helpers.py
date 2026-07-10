"""Хелперы для тестов валидации товаров."""

from app.infrastructure.xml.extractors import ProductItem


def make_product(
    offer_id: str,
    *,
    name: str | None = None,
    url: str = "https://mczgold.ru/catalog/item.html",
    category_id: str = "5",
    price_source: str = "1000",
    oldprice_source: str | None = None,
    url_source: str | None = None,
    available_source: str | None = "true",
    stock_source: str | None = None,
    pictures: list[str] | None = None,
) -> ProductItem:
    product_name = name if name is not None else f"Товар {offer_id}"
    resolved_url_source = url if url_source is None else url_source
    return ProductItem(
        offer_id=offer_id,
        name=product_name,
        name_source=product_name,
        vendor="MCZ",
        price=price_source or "",
        price_source=price_source,
        oldprice_source=oldprice_source,
        url=url,
        url_source=resolved_url_source,
        available_source=available_source,
        stock_source=stock_source,
        pictures=pictures or ["https://cdn.example/product.jpg"],
        category_id=category_id,
        raw={},
    )
