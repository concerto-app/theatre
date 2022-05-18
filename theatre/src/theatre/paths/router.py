from starlite import Router

from theatre.paths.connect.router import connect_router

router = Router(path="/", route_handlers=[connect_router])
