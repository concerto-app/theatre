from typing import Dict, Sequence

from theatre.models.data import Code, CodeEntry
from theatre.server.room import Room
from theatre.utils import FrozenModel, Timer


class InternalCode(FrozenModel):
    entries: Sequence[CodeEntry]

    @classmethod
    def new(cls, code: Code) -> "InternalCode":
        return cls(entries=tuple(code.entries))

    def code(self) -> Code:
        return Code(entries=list(self.entries))


class Server:
    rooms: Dict[InternalCode, Room]

    def __init__(self) -> None:
        self.rooms = {}

    async def cleanup(self) -> None:
        for room in self.rooms.values():
            await room.close()

    def _create_room(self, code: InternalCode) -> Room:
        room = Room(code.code())

        async def close() -> None:
            await room.close()
            self.rooms.pop(code, None)

        async def timeout() -> None:
            if len(room.users) == 0:
                await close()

        timer = Timer(60, timeout)

        @room.on("empty")
        async def on_empty() -> None:
            timer.cancel()
            await close()

        self.rooms[code] = room
        return room

    def get_room(self, code: Code) -> Room:
        code = InternalCode.new(code)
        room = self.rooms.get(code)
        if room is None:
            room = self._create_room(code)
        return room
