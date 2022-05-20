import random
import uuid
from dataclasses import dataclass
from typing import Dict, Optional, Set, Union

from pydantic import ValidationError
from pyee.asyncio import AsyncIOEventEmitter

from theatre.constants import AVAILABLE_AVATAR_EMOJI_IDS
from theatre.models.data import (
    Avatar,
    Emoji,
    IncomingUserMessage,
    OutgoingServerMessage,
    OutgoingUserMessage,
    User,
)
from theatre.server.connection import Connection
from theatre.utils import Timer


class NotEnoughResourcesError(Exception):
    pass


@dataclass
class UserInfo:
    data: User
    connection: Connection


class Room(AsyncIOEventEmitter):
    _users: Dict[str, UserInfo] = {}
    _connected_users: Set[str] = set()

    @property
    def users(self) -> Set[User]:
        users = set()
        for user_id in self._connected_users:
            user_data = self.get_user_data(user_id)
            if user_data is not None:
                users.add(user_data)
        return users

    def get_user_data(self, user_id: str) -> Optional[User]:
        return self._users[user_id].data

    async def close(self) -> None:
        for user_info in self._users.values():
            await user_info.connection.close()

    def pick_emoji(self) -> Emoji:
        used_ids = set(
            [
                user_info.data.avatar.emoji.id
                for user_info in self._users.values()
            ]
        )
        free_ids = AVAILABLE_AVATAR_EMOJI_IDS - used_ids
        if len(free_ids) == 0:
            raise NotEnoughResourcesError()
        picked_id = random.choice(tuple(free_ids))
        return Emoji(id=picked_id)

    def create_user(self) -> User:
        user_id = uuid.uuid4().hex
        avatar = Avatar(emoji=self.pick_emoji())
        return User(id=user_id, avatar=avatar)

    def broadcast(self, user_id: str, data: Union[str, bytes]) -> None:
        for connected_user_id in self._connected_users:
            if connected_user_id != user_id:
                user_info = self._users.get(connected_user_id)
                if user_info is not None:
                    user_info.connection.send(data)

    def handle_data(self, user_id: str, data: Union[str, bytes]) -> None:
        try:
            incoming_message = IncomingUserMessage.parse_raw(data)
        except ValidationError:
            return
        outgoing_message = OutgoingUserMessage(
            user=user_id,
            type=incoming_message.type,
            data=incoming_message.data,
        )
        data = outgoing_message.json()
        self.broadcast(user_id, data)

    def handle_disconnect(self, user_id: str) -> None:
        outgoing_message = OutgoingServerMessage(
            type="disconnect", data={"user": user_id}
        )
        data = outgoing_message.json()
        self.broadcast(user_id, data)

    def handle_connect(self, user_id: str) -> None:
        outgoing_message = OutgoingServerMessage(
            type="connect", data={"user": self.get_user_data(user_id)}
        )
        data = outgoing_message.json()
        self.broadcast(user_id, data)

    def add(self, connection: Connection) -> User:
        user = self.create_user()

        def cleanup() -> None:
            self._connected_users.discard(user.id)
            self._users.pop(user.id, None)
            if len(self._users) == 0:
                self.emit("empty")

        async def timeout() -> None:
            if user.id not in self._connected_users:
                cleanup()

        timer = Timer(60, timeout)

        @connection.on("connected")
        def on_connected() -> None:
            timer.cancel()
            self._connected_users.add(user.id)
            self.handle_connect(user.id)

        @connection.on("disconnected")
        def on_disconnected() -> None:
            self.handle_disconnect(user.id)
            cleanup()

        @connection.on("data")
        def on_data(message: Union[bytes, str]) -> None:
            self.handle_data(user.id, message)

        self._users[user.id] = UserInfo(data=user, connection=connection)
        return user
