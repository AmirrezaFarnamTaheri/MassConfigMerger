from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from rich.progress import Progress

from . import fetcher, generator, tester
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

        asyncio.run(run_pipeline(sources, output_dir))

    except FileNotFoundError:
        click.echo(f"Error: The sources file was not found at '{sources_file}'", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)
        sys.exit(1)


async def run_pipeline(sources: list[str], output_dir: str):
    """
    The main asynchronous pipeline for fetching, testing, and generating.
    """
    with Progress() as progress:
        # Step 1: Fetch configurations from all sources
        fetched_configs = await fetcher.fetch_all(sources, progress)
        if not fetched_configs:
            progress.console.print("[bold red]No configurations were fetched. Exiting.[/bold red]")
            return

        progress.console.print(
            f"[bold green]Successfully fetched {len(fetched_configs)} unique configurations.[/bold green]"
        )

        # Step 2: Test all fetched configurations
        tested_proxies = await tester.test_configs(fetched_configs, progress)
        working_proxies = [p for p in tested_proxies if p.is_working]
        progress.console.print(
            f"[bold green]Testing complete. Found {len(working_proxies)} working proxies.[/bold green]"
        )

        if not working_proxies:
            progress.console.print("[bold yellow]No working proxies found. No files will be generated.[/bold yellow]")
            return

        # Step 3: Generate the output files
        task = progress.add_task("[blue]Generating output files...", total=1)
        generator.generate_files(tested_proxies, output_dir)
        progress.update(task, advance=1)
        progress.console.print(
            f"[bold blue]Output files have been generated in '{output_dir}'.[/bold blue]"
        )


if __name__ == "__main__":
    main()