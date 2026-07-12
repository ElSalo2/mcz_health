"""Тесты расчёта HTTP-троттлинга."""

import pytest

from app.core.config import Settings
from app.services.monitoring.url_throttle import UrlThrottlePlanner


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("BOT_TOKEN", "1234567890:ABCDEFghijklmnopQRSTUVwxyz")
    monkeypatch.setenv("ADMIN_ID", "1")
    monkeypatch.setenv(
        "STORE_FEED_URL",
        "https://st.sunlight.net/media/feed/outlets/yandex_outlets_mcz.xml",
    )
    monkeypatch.setenv(
        "PRODUCT_FEED_URL",
        "https://st.sunlight.net/media/feed/anyquery_mcz.xml",
    )
    return Settings()


def test_http_url_slot_seconds_default(settings: Settings) -> None:
    assert settings.http_url_slot_seconds == 0.25


def test_estimate_http_phase_seconds(settings: Settings) -> None:
    assert settings.estimate_http_phase_seconds(47000) == pytest.approx(11750.0)


def test_plan_for_url_count_uses_fixed_slot(settings: Settings) -> None:
    planner = UrlThrottlePlanner(settings)
    slot = planner.plan_for_url_count(46768)
    assert slot == pytest.approx(0.25)
    assert planner.slot_seconds == pytest.approx(0.25)


def test_plan_for_zero_urls(settings: Settings) -> None:
    planner = UrlThrottlePlanner(settings)
    assert planner.plan_for_url_count(0) == 0.0


def test_seconds_until_next_request(settings: Settings) -> None:
    planner = UrlThrottlePlanner(settings)
    planner.plan_for_url_count(10)
    assert planner.seconds_until_next_request(0.0) == pytest.approx(0.25)
    assert planner.seconds_until_next_request(0.1) == pytest.approx(0.15)
    assert planner.seconds_until_next_request(0.25) == 0.0


def test_local_reserve_must_be_less_than_max_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BOT_TOKEN", "1234567890:ABCDEFghijklmnopQRSTUVwxyz")
    monkeypatch.setenv("ADMIN_ID", "1")
    monkeypatch.setenv(
        "STORE_FEED_URL",
        "https://st.sunlight.net/media/feed/outlets/yandex_outlets_mcz.xml",
    )
    monkeypatch.setenv(
        "PRODUCT_FEED_URL",
        "https://st.sunlight.net/media/feed/anyquery_mcz.xml",
    )
    monkeypatch.setenv("MAX_CHECK_DURATION_SECONDS", "600")
    monkeypatch.setenv("LOCAL_CHECK_RESERVE_SECONDS", "600")

    with pytest.raises(ValueError, match="LOCAL_CHECK_RESERVE_SECONDS"):
        Settings()
