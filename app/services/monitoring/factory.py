"""Сборка компонентов мониторинга."""

from __future__ import annotations

from app.core.config import Settings
from app.infrastructure.http.client import HttpClient
from app.infrastructure.http.resource_checker import ResourceChecker
from app.infrastructure.xml.extractors import FeedExtractor
from app.infrastructure.xml.parser import XmlParser
from app.services.continuous_monitoring_service import ContinuousMonitoringService
from app.services.monitoring.category_validator import CategoryValidator
from app.services.monitoring.change_detector import ChangeDetector
from app.services.monitoring.feed_availability import FeedAvailabilityChecker
from app.services.monitoring.feed_structure import FeedStructureChecker
from app.services.monitoring.image_checker import ImageChecker
from app.services.monitoring.orchestrator import CheckOrchestrator
from app.services.monitoring.price_validator import PriceValidator
from app.services.monitoring.product_validator import ProductValidator
from app.services.monitoring.stock_validator import StockValidator
from app.services.monitoring.store_validator import StoreValidator
from app.services.monitoring.url_throttle import UrlThrottlePlanner
from app.services.notification_service import NotificationService


async def build_monitoring_stack(
    config: Settings,
    session_factory,
    notification_service: NotificationService,
) -> tuple[HttpClient, CheckOrchestrator, ContinuousMonitoringService]:
    """Создаёт и связывает компоненты мониторинга."""
    http_client = HttpClient(timeout=config.request_timeout)
    await http_client.start()

    throttle_planner = UrlThrottlePlanner(config)
    resource_checker = ResourceChecker(http_client, throttle_planner)
    xml_parser = XmlParser()
    feed_extractor = FeedExtractor()
    change_detector = ChangeDetector(config)
    image_checker = ImageChecker(resource_checker, config)

    availability_checker = FeedAvailabilityChecker(http_client, config)
    structure_checker = FeedStructureChecker(xml_parser)
    category_validator = CategoryValidator()
    product_validator = ProductValidator(
        resource_checker,
        image_checker,
        feed_extractor,
        category_validator,
        config,
    )
    price_validator = PriceValidator(config)
    stock_validator = StockValidator()
    store_validator = StoreValidator(resource_checker, image_checker, change_detector, config)

    orchestrator = CheckOrchestrator(
        settings=config,
        session_factory=session_factory,
        availability_checker=availability_checker,
        structure_checker=structure_checker,
        store_validator=store_validator,
        product_validator=product_validator,
        price_validator=price_validator,
        stock_validator=stock_validator,
        change_detector=change_detector,
        feed_extractor=feed_extractor,
        resource_checker=resource_checker,
        throttle_planner=throttle_planner,
        notification_service=notification_service,
    )
    continuous_monitoring = ContinuousMonitoringService(
        config,
        orchestrator,
        notification_service,
    )
    return http_client, orchestrator, continuous_monitoring
