from starlite import Router

from theatre.paths.connect.router import connect_router
from theatre.paths.entries.router import entries_router

router = Router(path="/", route_handlers=[connect_router, entries_router])
