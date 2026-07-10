"""Человекочитаемые названия фидов."""

from app.domain.enums import FeedType

FEED_TYPE_LABELS: dict[FeedType, str] = {
    FeedType.PRODUCT: "Товары",
    FeedType.STORE: "Магазины",
}


def feed_label(feed_type: FeedType) -> str:
    return FEED_TYPE_LABELS[feed_type]
