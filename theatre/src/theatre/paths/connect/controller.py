from typing import AsyncIterator, Dict, Tuple

from pydantic import ValidationError
from starlette.websockets import WebSocketDisconnect
from starlite import (
    Controller,
    State,
    WebSocket,
    websocket,
)

from theatre.models.connect import (
    ConnectRequestMessage,
    ConnectResponseMessage,
    Message,
)
from theatre.models.data import User
from theatre.server.room import Room
from theatre.server.server import Server
from theatre.utils import gather


class ConnectController(Controller):
    path = None

    @staticmethod
    async def _connect(server: Server, socket: WebSocket) -> Tuple[User, Room]:
        request = ConnectRequestMessage.parse_obj(await socket.receive_json())
        room = server.get_room(request.code)
        user, other_users = await room.connect()
        response = ConnectResponseMessage(user=user, other_users=other_users)
        await socket.send_json(response.dict())
        return user, room

    @staticmethod
    async def _fetch_server(
        iterator: AsyncIterator[Dict], socket: WebSocket
    ) -> None:
        async for message in iterator:
            await socket.send_json(message)

    @staticmethod
    async def _fetch_client(user: User, room: Room, socket: WebSocket) -> None:
        while True:
            message = await socket.receive_json()
            try:
                message = Message.parse_obj(message).__root__
            except ValidationError:
                continue
            if message.type == "offer":
                await room.make_offer(
                    user.id, message.to_user, message.session
                )
            elif message.type == "answer":
                await room.make_answer(
                    user.id, message.to_user, message.session
                )

    @websocket()
    async def connect(self, state: State, socket: WebSocket) -> None:
        server: Server = state.server
        user, room = None, None

        try:
            await socket.accept()

            user, room = await self._connect(server, socket)

            await gather(
                self._fetch_server(room.fetch(user.id), socket),
                self._fetch_client(user, room, socket),
            )
        except (WebSocketDisconnect, ConnectionError, RuntimeError):
            pass
        finally:
            try:
                if room is not None and user is not None:
                    await room.disconnect(user.id)
            finally:
                try:
                    await socket.close()
                except (ConnectionError, RuntimeError):
                    pass
