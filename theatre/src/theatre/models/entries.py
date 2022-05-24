from typing import Sequence

from theatre.models.data import Emoji
from theatre.utils import FrozenModel


class EntriesResponse(FrozenModel):
    available: Sequence[Emoji]
