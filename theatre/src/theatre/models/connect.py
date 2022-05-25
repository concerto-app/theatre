from typing import List, Literal, Union

from pydantic import Field

from theatre.models.data import Code, Session, User
from theatre.utils import FrozenModel


class ConnectRequestMessage(FrozenModel):
    type: Literal["connect-request"] = "connect-request"
    code: Code


class ConnectResponseMessage(FrozenModel):
    type: Literal["connect-response"] = "connect-response"
    user: User
    other_users: List[User]


class ConnectedMessage(FrozenModel):
    type: Literal["connected"] = "connected"
    user: User


class DisconnectedMessage(FrozenModel):
    type: Literal["disconnected"] = "disconnected"
    user: str


class OfferMessage(FrozenModel):
    type: Literal["offer"] = "offer"
    from_user: str
    to_user: str
    session: Session


class AnswerMessage(FrozenModel):
    type: Literal["answer"] = "answer"
    from_user: str
    to_user: str
    session: Session


class Message(FrozenModel):
    __root__: Union[
        ConnectRequestMessage,
        ConnectResponseMessage,
        ConnectedMessage,
        DisconnectedMessage,
        OfferMessage,
        AnswerMessage,
    ] = Field(..., discriminator="type")
