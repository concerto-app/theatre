from typing import Dict, Sequence, Tuple

from theatre.models.data import Code, CodeEntry, Session, User
from theatre.server.connection import Connection
from theatre.server.room import Room
from theatre.utils import FrozenModel, Timer


class InternalCode(FrozenModel):
    entries: Sequence[CodeEntry]

    @classmethod
    def new(cls, code: Code) -> "InternalCode":
        return cls(entries=tuple(code.entries))


class Server:
    rooms: Dict[InternalCode, Room] = {}

    async def cleanup(self) -> None:
        for room in self.rooms.values():
            await room.close()

    def create_room(self, code: InternalCode) -> Room:
        room = Room()

        async def close() -> None:
            await room.close()
            self.rooms.pop(code, None)

        @room.on("empty")
        async def on_empty() -> None:
            await close()

        async def timeout() -> None:
            if len(room.users) == 0:
                await close()

        Timer(60, timeout)

        self.rooms[code] = room
        return room

    def get_room(self, code: Code) -> Room:
        code = InternalCode.new(code)
        room = self.rooms.get(code)
        if room is None:
            room = self.create_room(code)
        return room

    async def connect(
        self, code: Code, session: Session
    ) -> Tuple[User, Session]:
        room = self.get_room(code)
        connection = await Connection.new(session)
        user = room.add(connection)
        return user, connection.session
