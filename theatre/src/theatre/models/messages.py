from typing import Literal, Optional

from theatre.utils import FrozenModel


class KeyboardActionData(FrozenModel):
    note: int
    velocity: int


class IncomingAction(FrozenModel):
    type: Literal["press", "release"]
    data: KeyboardActionData


class IncomingMessage(FrozenModel):
    action: IncomingAction


class OutgoingAction(FrozenModel):
    type: Literal["press", "release", "disconnect"]
    data: Optional[KeyboardActionData] = None


class OutgoingMessage(FrozenModel):
    user_id: str
    action: OutgoingAction
