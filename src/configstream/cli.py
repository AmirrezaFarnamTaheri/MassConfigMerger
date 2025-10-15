from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from rich.progress import Progress

from . import pipeline
from .config import settings


@click.group()
def main():
    """
    ConfigStream: Automated VPN Configuration Aggregator.
    """
    pass


@main.command()
@click.option(
    "--sources",
    "sources_file",
    default=settings.sources_file,
    help="Path to the file containing source URLs.",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--output",
    "output_dir",
    default=settings.output_dir,
    help="Directory to save the generated files.",
    type=click.Path(file_okay=False),
)
def merge(sources_file: str, output_dir: str):
    """
    Run the full pipeline: fetch from sources, test proxies, and generate outputs.
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        sources = Path(sources_file).read_text().splitlines()
        sources = [s.strip() for s in sources if s.strip() and not s.startswith("#")]
        if not sources:
            click.echo("No sources found in the specified file.", err=True)
            return

        with Progress() as progress:
            asyncio.run(pipeline.run_full_pipeline(sources, output_dir, progress))

    except FileNotFoundError:
        click.echo(f"Error: The sources file was not found at '{sources_file}'", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()