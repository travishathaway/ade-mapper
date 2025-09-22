"""ADE Mapper CLI."""

import typer

from .main import main

app = typer.Typer()


@app.command()
def collect() -> None:
    """
    Collects data related to ADE events
    """
    main()

