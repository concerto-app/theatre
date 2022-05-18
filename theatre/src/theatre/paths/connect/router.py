from starlite import Router

from theatre.paths.connect.controller import ConnectController

connect_router = Router(path="/connect", route_handlers=[ConnectController])
