from typing import Dict, Literal, Sequence

from theatre.utils import FrozenModel


class Session(FrozenModel):
    description: str


class Emoji(FrozenModel):
    id: str


class CodeEntry(FrozenModel):
    emoji: Emoji


class Code(FrozenModel):
    entries: Sequence[CodeEntry]


class Avatar(FrozenModel):
    emoji: Emoji


class User(FrozenModel):
    id: str
    avatar: Avatar


class OutgoingUserMessage(FrozenModel):
    user: str
    type: str
    data: Dict


class OutgoingServerMessage(FrozenModel):
    type: str
    data: Dict


class IncomingUserMessage(FrozenModel):
    type: str
    data: Dict
