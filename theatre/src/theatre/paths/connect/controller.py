from starlette.status import HTTP_423_LOCKED
from starlite import Controller, HTTPException, State, post

from theatre.models.connect import ConnectRequest, ConnectResponse
from theatre.server.room import NotEnoughResourcesError
from theatre.server.server import Server


class ConnectController(Controller):
    path = None

    @post()
    async def connect(
        self, state: State, data: ConnectRequest
    ) -> ConnectResponse:
        try:
            server: Server = state.server
            user, connected_users, session = await server.connect(
                data.code, data.session
            )
            return ConnectResponse(
                user=user,
                connected_users=list(connected_users),
                session=session,
            )
        except NotEnoughResourcesError:
            raise HTTPException(
                "Maximum players limit reached",
                status_code=HTTP_423_LOCKED,
            )
