import logging
from logging.config import dictConfig

from pydantic import BaseModel


class LogConfig(BaseModel):
    version = 1
    disable_existing_loggers = False
    formatters = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s | %(asctime)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    }
    loggers = {
        "theatre": {"handlers": ["default"], "level": "DEBUG"},
    }


dictConfig(LogConfig().dict())
logger = logging.getLogger("theatre")
