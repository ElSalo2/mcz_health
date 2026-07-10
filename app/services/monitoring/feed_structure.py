"""Этап 2: проверка структуры XML."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.exceptions import FeedParseError
from app.domain.entities.issue import Issue
from app.domain.enums import FeedType, IssueCategory, Severity
from app.infrastructure.xml.parser import ParsedFeed, XmlParser
from app.services.monitoring.feed_labels import feed_label
from app.services.monitoring.issue_registry import IssueRegistry

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class StructureResult:
    """Результат проверки структуры XML."""

    valid: bool
    parsed: ParsedFeed | None
    issue: Issue | None = None


class FeedStructureChecker:
    """Проверяет структуру и парсинг XML."""

    def __init__(self, xml_parser: XmlParser) -> None:
        self._xml_parser = xml_parser

    def check(self, content: bytes, feed_type: FeedType) -> StructureResult:
        """Парсит XML и проверяет его структуру."""
        try:
            parsed = self._xml_parser.parse(content, feed_type.value)
            self._xml_parser.validate_structure(parsed, feed_type.value)
            return StructureResult(valid=True, parsed=parsed)
        except FeedParseError as exc:
            issue = Issue(
                fingerprint=IssueRegistry.build_fingerprint(
                    IssueCategory.FEED_PARSE,
                    feed_type,
                ),
                severity=Severity.CRITICAL,
                category=IssueCategory.FEED_PARSE,
                feed_type=feed_type,
                message_key="XML_ERROR",
                context={"feed_name": feed_label(feed_type), "reason": str(exc)},
            )
            return StructureResult(valid=False, parsed=None, issue=issue)
