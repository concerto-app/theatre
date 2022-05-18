from theatre.models.data import Code, Session, User
from theatre.utils import FrozenModel


class ConnectRequest(FrozenModel):
    code: Code
    session: Session


class ConnectResponse(FrozenModel):
    user: User
    session: Session
