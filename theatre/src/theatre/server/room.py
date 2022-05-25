import logging
import random
import uuid
from asyncio import AbstractEventLoop, Queue
from typing import (
    Any,
    AsyncIterator,
    Container,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
)

from pyee.asyncio import AsyncIOEventEmitter

from theatre.constants import AVAILABLE_AVATAR_EMOJI_IDS
from theatre.log import logger
from theatre.models.connect import (
    AnswerMessage,
    ConnectedMessage,
    DisconnectedMessage,
    OfferMessage,
)
from theatre.models.data import (
    Avatar,
    Code,
    Emoji,
    Session,
    User,
)


class NotEnoughResourcesError(Exception):
    pass


class RoomLoggerAdapter(logging.LoggerAdapter):
    def __init__(self, base_logger, code: Code) -> None:
        super().__init__(base_logger, {})
        self.code = code

    def process(self, msg, kwargs):
        prefix = " ".join([str(entry.emoji) for entry in self.code.entries])
        return f"[ {prefix} ] {msg}", kwargs


Message = Optional[Dict[str, Any]]


class Room(AsyncIOEventEmitter):
    _code: Code
    _users: Dict[str, User]
    _queues: Dict[str, Queue[Message]]

    def __init__(self, code: Code, loop: Optional[AbstractEventLoop] = None):
        super().__init__(loop)
        self._code = code
        self._logger = RoomLoggerAdapter(logger, code=code)
        self._users = {}
        self._queues = {}
        self._logger.info("Room created.")

    @property
    def users(self) -> List[User]:
        return [user for user in self._users.values()]

    def _pick_emoji(self) -> Emoji:
        used_ids = set([user.avatar.emoji.id for user in self._users.values()])
        free_ids = AVAILABLE_AVATAR_EMOJI_IDS - used_ids
        if len(free_ids) == 0:
            raise NotEnoughResourcesError()
        picked_id = random.choice(tuple(free_ids))
        return Emoji(id=picked_id)

    def _create_user(self) -> User:
        user_id = uuid.uuid4().hex
        avatar = Avatar(emoji=self._pick_emoji())
        return User(id=user_id, avatar=avatar)

    async def _broadcast_to(
        self, message: Message, to: Union[str, Container[str]]
    ) -> None:
        to = {to} if isinstance(to, str) else to
        queues = [queue for user, queue in self._queues.items() if user in to]
        for queue in queues:
            await queue.put(message)

    async def _broadcast_all(self, message: Message) -> None:
        await self._broadcast_to(message, self._users.keys())

    async def _broadcast_except(
        self, message: Message, exception: str
    ) -> None:
        to = set(self._users.keys()) - {exception}
        await self._broadcast_to(message, to)

    async def _broadcast_connect(self, connected_user: User) -> None:
        message = ConnectedMessage(user=connected_user)
        await self._broadcast_except(
            message.dict(),
            connected_user.id,
        )

    async def _broadcast_disconnect(self, disconnected_user: User) -> None:
        message = DisconnectedMessage(user=disconnected_user.id)
        await self._broadcast_except(
            message.dict(),
            disconnected_user.id,
        )

    async def _signal(
        self,
        type: Literal["offer", "answer"],
        from_user: str,
        to_user: str,
        session: Session,
    ) -> None:
        queue = self._queues[to_user]
        if type == "offer":
            message = OfferMessage(
                from_user=from_user, to_user=to_user, session=session
            )
        elif type == "answer":
            message = AnswerMessage(
                from_user=from_user, to_user=to_user, session=session
            )
        else:
            return
        await queue.put(message.dict())

    async def connect(self) -> Tuple[User, List[User]]:
        self._logger.info("New connection.")

        new_user = self._create_user()
        other_users = list(self._users.values())

        self._logger.info(f"Created user {new_user.avatar.emoji}.")

        self._users[new_user.id] = new_user
        self._queues[new_user.id] = Queue()

        await self._broadcast_connect(new_user)

        return new_user, other_users

    async def disconnect(self, user: str) -> None:
        user = self._users.get(user, None)
        if user is None:
            return

        self._logger.info(f"User {user.avatar.emoji} disconnected.")

        self._queues.pop(user.id, None)
        self._users.pop(user.id, None)

        await self._broadcast_disconnect(user)

        if len(self._users) == 0:
            self.emit("empty")

    async def close(self) -> None:
        self._logger.info("Room closed.")
        await self._broadcast_all(None)

    async def make_offer(
        self, from_user: str, to_user: str, session: Session
    ) -> None:
        from_user = self._users[from_user]
        to_user = self._users[to_user]
        self._logger.info(
            f"Offer from {from_user.avatar.emoji} to {to_user.avatar.emoji}."
        )
        await self._signal("offer", from_user.id, to_user.id, session)

    async def make_answer(
        self, from_user: str, to_user: str, session: Session
    ) -> None:
        from_user = self._users[from_user]
        to_user = self._users[to_user]
        self._logger.info(
            f"Answer from {from_user.avatar.emoji} to {to_user.avatar.emoji}."
        )
        await self._signal("answer", from_user.id, to_user.id, session)

    async def fetch(self, user: str) -> AsyncIterator[Dict]:
        user = self._users[user]
        queue = self._queues[user.id]
        while True:
            message = await queue.get()
            if message is None:
                return
            self._logger.debug(f"New message for user {user.avatar.emoji}.")
            yield message
