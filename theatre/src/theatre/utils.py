import asyncio
from typing import Awaitable, Callable

from pydantic import BaseModel


class FrozenModel(BaseModel):
    class Config:
        frozen = True


class Timer:
    def __init__(
        self, timeout: float, callback: Callable[[], Awaitable]
    ) -> None:
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.create_task(self._job())

    async def _job(self) -> None:
        await asyncio.sleep(self._timeout)
        await self._callback()

    def cancel(self) -> bool:
        return self._task.cancel()
