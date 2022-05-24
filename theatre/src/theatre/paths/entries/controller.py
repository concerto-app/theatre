from typing import List

from starlite import Controller, State, get

from theatre.models.data import Emoji
from theatre.models.entries import EntriesResponse


class EntriesController(Controller):
    path = None

    @get()
    def entries(self, state: State) -> EntriesResponse:
        entries: List[str] = state.entries
        return EntriesResponse(
            available=[Emoji(id=entry) for entry in entries]
        )
