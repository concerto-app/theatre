from typing import Dict, Sequence, Set, Tuple

from theatre.models.data import Code, CodeEntry, Session, User
from theatre.server.connection import Connection
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

    def create_room(self, code: InternalCode) -> Room:
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
            room = self.create_room(code)
        return room

    async def connect(
        self, code: Code, session: Session
    ) -> Tuple[User, Set[User], Session]:
        room = self.get_room(code)
        connection = await Connection.new(session)
        user = room.add(connection)
        connected_users = room.users
        return user, connected_users, connection.session
