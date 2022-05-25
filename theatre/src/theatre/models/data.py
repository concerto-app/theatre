from typing import Sequence

from theatre.utils import FrozenModel


class Session(FrozenModel):
    description: str


class Emoji(FrozenModel):
    id: str

    def __str__(self) -> str:
        return chr(int(self.id, 16))


class CodeEntry(FrozenModel):
    emoji: Emoji


class Code(FrozenModel):
    entries: Sequence[CodeEntry]


class Avatar(FrozenModel):
    emoji: Emoji


class User(FrozenModel):
    id: str
    avatar: Avatar
