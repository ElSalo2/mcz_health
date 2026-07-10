"""Единый обработчик ошибок для различных слоёв приложения."""

import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def handle_service_errors(
    func: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    """Декоратор для перехвата и логирования ошибок сервисного слоя."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await func(*args, **kwargs)
        except AppError:
            raise
        except Exception as exc:
            logger.exception("Необработанная ошибка в %s", func.__name__)
            raise AppError(
                f"Внутренняя ошибка при выполнении {func.__name__}",
                details={"original": str(exc)},
            ) from exc

    return wrapper
