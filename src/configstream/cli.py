from __future__ import annotations

import asyncio
import sys
import json
from pathlib import Path

import click
from rich.progress import Progress
from rich.console import Console

from . import pipeline
from .config import settings
from .core import Proxy
from .geoip import download_geoip_dbs

console = Console()

@click.group()
@click.version_option(version="1.0.0")
def main():
    """
    ConfigStream: Automated VPN Configuration Aggregator.
    """
    pass


@main.command()
@click.option(
    "--sources",
    "sources_file",
    required=True,
    help="Path to the file containing source URLs.",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--output",
    "output_dir",
    default=settings.output_dir,
    help="Directory to save generated files.",
    type=click.Path(file_okay=False),
)
@click.option(
    "--max-proxies",
    "max_proxies",
    default=None,
    help="Maximum number of proxies to test.",
    type=int,
)
@click.option(
    "--country",
    "country",
    default=None,
    help="Filter proxies by country code (e.g., US, DE).",
    type=str,
)
@click.option(
    "--min-latency",
    "min_latency",
    default=None,
    help="Minimum latency in milliseconds.",
    type=float,
)
@click.option(
    "--max-latency",
    "max_latency",
    default=None,
    help="Maximum latency in milliseconds.",
    type=float,
)
@click.option(
    "--max-workers",
    "max_workers",
    default=10,
    help="Maximum number of concurrent workers.",
    type=int,
)
@click.option(
    "--timeout",
    "timeout",
    default=10,
    help="Timeout in seconds for testing each proxy.",
    type=int,
)
def merge(
    sources_file: str,
    output_dir: str,
    max_proxies: int | None,
    country: str | None,
    min_latency: float | None,
    max_latency: float | None,
    max_workers: int,
    timeout: int,
):
    """
    Run the full pipeline: fetch, test, and generate outputs.
    """
    # Download GeoIP databases
    console.print("Checking for GeoIP databases...")
    asyncio.run(download_geoip_dbs())

    # Set event loop policy for Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        # Read sources
        sources = Path(sources_file).read_text().splitlines()
        sources = [s.strip() for s in sources if s.strip() and not s.startswith("#")]

        if not sources:
            click.echo("✗ No sources found in the specified file.", err=True)
            sys.exit(1)

        click.echo(f"✓ Loaded {len(sources)} sources")

        # Update settings
        settings.test_max_workers = max_workers
        settings.test_timeout = timeout

        # Run pipeline
        with Progress() as progress:
            asyncio.run(
                pipeline.run_full_pipeline(
                    sources,
                    output_dir,
                    progress,
                    max_proxies=max_proxies,
                    country=country,
                    min_latency=min_latency,
                    max_latency=max_latency,
                )
            )

        click.echo("\n✓ Pipeline completed successfully!")
        click.echo(f"✓ Output files saved to: {output_dir}")

    except FileNotFoundError:
        click.echo(f"✗ Sources file not found: {sources_file}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ An error occurred: {e}", err=True)
        sys.exit(1)


@main.command()
def update_databases():
    """
    Update GeoIP databases.
    """
    console.print("Updating GeoIP databases...")
    success = asyncio.run(download_geoip_dbs())

    if success:
        console.print("✅ All databases updated successfully!")
    else:
        console.print("❌ Some databases failed to update.")
        console.print("   Check MAXMIND_LICENSE_KEY environment variable or GitHub secret.")

@main.command()
@click.option(
    "--input",
    "input_file",
    default="output/proxies.json",
    help="Path to the proxies JSON file.",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--output",
    "output_dir",
    default=settings.output_dir,
    help="Directory to save generated files.",
    type=click.Path(file_okay=False),
)
@click.option(
    "--timeout",
    "timeout",
    default=8,
    help="Timeout in seconds for testing each proxy.",
    type=int,
)
@click.option(
    "--max-workers",
    "max_workers",
    default=15,
    help="Maximum number of concurrent workers.",
    type=int,
)
def retest(input_file: str, output_dir: str, timeout: int, max_workers: int):
    """
    Retest proxies from a JSON file.
    """
    # Set event loop policy for Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        # Read proxies from file
        with open(input_file, "r") as f:
            proxies_data = json.load(f)

        if not proxies_data:
            click.echo("✗ No proxies found in the specified file.", err=True)
            sys.exit(1)

        click.echo(f"✓ Loaded {len(proxies_data)} proxies")

        # Create Proxy objects
        proxies = [Proxy(**p) for p in proxies_data]

        # Update settings
        settings.test_timeout = timeout
        settings.test_max_workers = max_workers

        # Run pipeline
        with Progress() as progress:
            asyncio.run(
                pipeline.run_full_pipeline(
                    [],
                    output_dir,
                    progress,
                    proxies=proxies,
                )
            )

        click.echo("\n✓ Retest completed successfully!")
        click.echo(f"✓ Output files saved to: {output_dir}")

    except FileNotFoundError:
        click.echo(f"✗ Input file not found: {input_file}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ An error occurred: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()