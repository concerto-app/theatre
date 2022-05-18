"""Main script.

This module provides basic CLI entrypoint.

"""

import typer
import uvicorn

from theatre.app import app
from theatre.config import config

cli = typer.Typer()


@cli.command()
def main(
    host: str = typer.Option(
        default="0.0.0.0", help="Host to run the server on"
    ),
    port: int = typer.Option(
        default=config.port, help="Port to run the server on"
    ),
):
    """Command line interface for theatre."""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    cli()
