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


async def gather(*tasks, **kwargs):
    tasks = [
        task if isinstance(task, asyncio.Task) else asyncio.create_task(task)
        for task in tasks
    ]
    try:
        return await asyncio.gather(*tasks, **kwargs)
    except BaseException as e:
        for task in tasks:
            task.cancel()
        raise e
