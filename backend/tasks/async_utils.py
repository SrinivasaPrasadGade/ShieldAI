"""Async helpers for synchronous Celery worker tasks."""

import asyncio
from typing import Coroutine, TypeVar

T = TypeVar("T")
_loop: asyncio.AbstractEventLoop | None = None


def run_async(coro: Coroutine[object, object, T]) -> T:
    """Run a coroutine on a reusable event loop for this worker process."""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop.run_until_complete(coro)
