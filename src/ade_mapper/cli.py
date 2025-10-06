"""ADE Mapper CLI."""

import typer

from .main import main
from .cache import clear_cache

app = typer.Typer()


@app.command()
def collect() -> None:
    """
    Collects data related to ADE events
    """
    main()


@app.command()
def clean() -> None:
    """
    Cleans up cache directory
    """
    clear_cache()
    typer.echo("Cache cleaned 🧹 🧼")
