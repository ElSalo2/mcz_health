"""Определение ответов антибот-защиты (QRATOR и аналоги)."""

from __future__ import annotations

from app.infrastructure.http.client import HttpResponse

WAF_CHALLENGE_MARKERS = (
    b"__qrator/qauth.js",
    b"/__qrator/",
    b"qrator_jsr",
)


def is_waf_challenge(response: HttpResponse) -> bool:
    """
    True, если ответ похож на JS-challenge WAF, а не на реальную ошибку страницы.

    QRATOR на mczgold.ru часто отдаёт 401 с коротким HTML и qauth.js на GET,
    тогда как HEAD для той же страницы возвращает 200.
    """
    if response.status_code not in (401, 403, 429):
        return False

    body = response.content
    if not body:
        return False

    body_lower = body.lower()
    return any(marker in body_lower for marker in WAF_CHALLENGE_MARKERS)
