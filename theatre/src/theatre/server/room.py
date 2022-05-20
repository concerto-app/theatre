import asyncio
import logging
import random
import uuid
from asyncio import AbstractEventLoop
from dataclasses import dataclass
from typing import Dict, Optional, Set, Union

from pydantic import ValidationError
from pyee.asyncio import AsyncIOEventEmitter

from theatre.constants import AVAILABLE_AVATAR_EMOJI_IDS
from theatre.log import logger
from theatre.models.data import (
    Avatar,
    Code,
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


class RoomLoggerAdapter(logging.LoggerAdapter):
    def __init__(self, base_logger, code: Code) -> None:
        super().__init__(base_logger, {})
        self.code = code

    def process(self, msg, kwargs):
        prefix = " ".join([str(entry.emoji) for entry in self.code.entries])
        return f"[ {prefix} ] {msg}", kwargs


@dataclass
class UserInfo:
    data: User
    connection: Connection


class Room(AsyncIOEventEmitter):
    _code: Code
    _users: Dict[str, UserInfo]
    _connected_users: Set[str]

    def __init__(self, code: Code, loop: Optional[AbstractEventLoop] = None):
        super().__init__(loop)
        self._code = code
        self._logger = RoomLoggerAdapter(logger, code=code)
        self._users = {}
        self._connected_users = set()

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

    async def broadcast(self, user_id: str, data: Union[str, bytes]) -> None:
        async def send_to_user(
            data: Union[str, bytes], user_info: UserInfo
        ) -> None:
            await user_info.connection.send(data)

        user_infos = [
            self._users.get(connected_user_id)
            for connected_user_id in self._connected_users
            if connected_user_id != user_id
        ]
        tasks = [
            send_to_user(data, user_info)
            for user_info in user_infos
            if user_info is not None
        ]

        if len(tasks) > 0:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def handle_data(self, user_id: str, data: Union[str, bytes]) -> None:
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
        await self.broadcast(user_id, data)

    async def handle_disconnect(self, user_id: str) -> None:
        outgoing_message = OutgoingServerMessage(
            type="disconnect", data={"user": user_id}
        )
        data = outgoing_message.json()
        await self.broadcast(user_id, data)

    async def handle_connect(self, user_id: str) -> None:
        outgoing_message = OutgoingServerMessage(
            type="connect", data={"user": self.get_user_data(user_id)}
        )
        data = outgoing_message.json()
        await self.broadcast(user_id, data)

    def add(self, connection: Connection) -> User:
        self._logger.info("New connection.")

        user = self.create_user()

        def cleanup() -> None:
            self._connected_users.discard(user.id)
            self._users.pop(user.id, None)
            if len(self._users) == 0:
                self.emit("empty")

        async def timeout() -> None:
            if user.id not in self._connected_users:
                self._logger.info(
                    f"User {user.avatar.emoji} didn't connect on time."
                )
                cleanup()

        timer = Timer(60, timeout)

        @connection.on("connected")
        async def on_connected() -> None:
            self._logger.info(f"User {user.avatar.emoji} connected.")
            timer.cancel()
            self._connected_users.add(user.id)
            await self.handle_connect(user.id)

        @connection.on("disconnected")
        async def on_disconnected() -> None:
            self._logger.info(f"User {user.avatar.emoji} disconnected.")
            await self.handle_disconnect(user.id)
            cleanup()

        @connection.on("data")
        async def on_data(message: Union[bytes, str]) -> None:
            self._logger.info(f"User {user.avatar.emoji} sent message.")
            await self.handle_data(user.id, message)

        self._users[user.id] = UserInfo(data=user, connection=connection)
        return user
