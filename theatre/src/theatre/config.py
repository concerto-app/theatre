import os

from pydantic import BaseModel


class Config(BaseModel):
    port: int = int(os.getenv("THEATRE_PORT", 54321))


config = Config()
