"""Группировка проблем проверки по типам."""

from __future__ import annotations

from collections import Counter

from app.domain.entities.issue import Issue


def count_issues_by_type(issues: list[Issue]) -> tuple[dict[str, int], dict[str, int]]:
    """Возвращает счётчики предупреждений и критических ошибок по message_key."""
    warnings: Counter[str] = Counter()
    critical: Counter[str] = Counter()
    for issue in issues:
        if issue.severity.value == "warning":
            warnings[issue.message_key] += 1
        elif issue.severity.value == "critical":
            critical[issue.message_key] += 1
    return dict(warnings), dict(critical)
