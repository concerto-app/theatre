from starlite import CORSConfig, Starlite, State

from theatre.paths.router import router
from theatre.server.server import Server


async def setup(state: State) -> None:
    state.server = Server()


async def cleanup(state: State) -> None:
    server: Server = state.server
    await server.cleanup()


app = Starlite(
    route_handlers=[router],
    on_startup=[setup],
    on_shutdown=[cleanup],
    cors_config=CORSConfig(),
)
