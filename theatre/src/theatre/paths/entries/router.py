from starlite import Router

from theatre.paths.entries.controller import EntriesController

entries_router = Router(path="/entries", route_handlers=[EntriesController])
