"""Healthcheck-эндпоинты."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Проверка работоспособности приложения."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict[str, str]:
    """Проверка готовности приложения к работе."""
    return {"status": "ready"}
