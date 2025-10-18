from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress

from . import pipeline
from .config import AppSettings
from .core import Proxy
from .geoip import download_geoip_dbs
from .logging_config import setup_logging

console = Console()
config = AppSettings()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    ConfigStream: Automated VPN Configuration Aggregator.
    """
    setup_logging(config.LOG_LEVEL, config.MASK_SENSITIVE_DATA)


@cli.command()
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
    default="output",
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
    "country_filter",
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
    default=25,
    help="Maximum number of concurrent workers for testing.",
    type=int,
)
@click.option(
    "--timeout",
    "timeout",
    default=10,
    help="Timeout for testing each proxy.",
    type=int,
)
@click.option(
    "--verbose",
    "verbose",
    is_flag=True,
    default=False,
    help="Enable verbose output.",
)
def merge(
    sources_file: str,
    output_dir: str,
    max_proxies: int | None,
    country_filter: str | None,
    min_latency: float | None,
    max_latency: float | None,
    max_workers: int,
    timeout: int,
    verbose: bool,
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
        sources = [
            s.strip() for s in sources if s.strip() and not s.startswith("#")
        ]

        if not sources:
            click.echo("✗ No sources found in the specified file.", err=True)
            sys.exit(1)

        click.echo(f"✓ Loaded {len(sources)} sources")

        # Run pipeline
        with Progress() as progress:
            result = asyncio.run(
                pipeline.run_full_pipeline(
                    sources,
                    output_dir,
                    progress,
                    max_workers=max_workers,
                    max_proxies=max_proxies,
                    min_latency=min_latency,
                    max_latency=max_latency,
                    timeout=timeout,
                    country_filter=country_filter,
                ))

        if not result["success"]:
            click.echo(f"\n✗ Pipeline failed: {result['error']}", err=True)
            sys.exit(1)

        click.echo("\n✓ Pipeline completed successfully!")
        click.echo(f"✓ Output files saved to: {output_dir}")

    except FileNotFoundError:
        click.echo(f"✗ Sources file not found: {sources_file}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ An error occurred: {e}", err=True)
        sys.exit(1)


@cli.command()
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
        console.print(
            "   Check MAXMIND_LICENSE_KEY environment variable or GitHub secret."
        )


@cli.command()
@click.option(
    "--input",
    "input_file",
    default="output/proxies.json",
    help="Path to the proxies JSON file to retest",
    type=click.Path(dir_okay=False),
)
@click.option(
    "--output",
    "output_dir",
    default="output",
    help="Directory to save retest results",
    type=click.Path(file_okay=False),
)
@click.option(
    "--max-workers",
    type=int,
    default=10,
    help="Number of concurrent proxy tests",
)
@click.option(
    "--timeout",
    type=int,
    default=10,
    help="Timeout per proxy test in seconds",
)
@click.pass_context
def retest(
    ctx: click.Context,
    input_file: str,
    output_dir: str,
    max_workers: int,
    timeout: int,
) -> None:
    """
    Retest previously tested proxies from a JSON file.
    
    This command reads a proxies.json file (from a previous merge run),
    re-tests each proxy for availability and latency, then generates
    updated output files.
    
    Examples:
        configstream retest --input output/proxies.json --output output/
        configstream retest --input old_proxies.json --max-workers 20
    """
    # Set event loop policy for Windows compatibility
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    input_path = Path(input_file)
    output_path = Path(output_dir)
    
    # Determine if the input path was explicitly provided by the user
    # or if we're using the default value. This is critical for proper error handling.
    input_source = ctx.get_parameter_source('input_file')
    is_default_path = (input_source == click.core.ParameterSource.DEFAULT)
    
    try:
        # ===== STEP 1: Load JSON from file =====
        # Try to open and parse the file. We catch FileNotFoundError and
        # JSONDecodeError separately so we can provide context-appropriate messages.
        try:
            with open(input_path, 'r') as f:
                proxies_data = json.load(f)
        
        except FileNotFoundError:
            # File doesn't exist. How we report this depends on whether the user
            # explicitly provided the path or is using our default.
            if is_default_path:
                # User didn't specify --input, so we're using our default.
                # From their perspective, they just don't have proxies to retest yet.
                click.echo("No proxies found in the input file.", err=True)
                sys.exit(1)
            else:
                # User explicitly provided a path that doesn't exist.
                # This is a parameter validation error (exit code 2).
                click.echo(f"File '{input_file}' does not exist", err=True)
                sys.exit(2)
        
        except json.JSONDecodeError as e:
            # The file exists but contains invalid JSON.
            # Extract the specific error message (e.g., "Expecting property name")
            # so the user knows exactly what's wrong with their JSON.
            error_msg = str(e)
            click.echo(f"An error occurred: {error_msg}", err=True)
            sys.exit(1)
        
        # ===== STEP 2: Validate we have proxies =====
        # Check if the JSON file contained an empty list or null.
        if not proxies_data or len(proxies_data) == 0:
            click.echo("No proxies found in the input file.", err=True)
            sys.exit(1)
        
        # Successfully loaded proxies from file
        click.echo(f"✓ Loaded {len(proxies_data)} proxies")
        
        # ===== STEP 3: Reconstruct Proxy objects =====
        # Convert JSON objects back into Proxy instances.
        # We attempt to load all proxies but skip any that can't be constructed
        # (e.g., missing required fields). This is more resilient than failing
        # completely if a single proxy is malformed.
        proxies: list[Proxy] = []
        skipped_count = 0
        
        for proxy_data in proxies_data:
            try:
                # Try to create a Proxy from the JSON data
                proxy = Proxy(**proxy_data)
                proxies.append(proxy)
            except (TypeError, ValueError):
                # This proxy has invalid structure (missing fields, wrong types, etc.)
                # Skip it and continue with others
                skipped_count += 1
        
        # If we skipped some but have valid ones, that's OK. Show a warning.
        if skipped_count > 0:
            click.echo(f"⚠ Skipped {skipped_count} invalid proxy definitions", err=False)
        
        # If no valid proxies could be constructed, fail
        if not proxies:
            click.echo("No proxies found in the input file.", err=True)
            sys.exit(1)
        
        click.echo(f"✓ Validated {len(proxies)} proxy definitions")
        
        # ===== STEP 4: Run retest pipeline =====
        # Execute the full proxy testing pipeline with our loaded proxies.
        # We pass an empty sources list since we're retesting existing proxies,
        # not fetching new ones from sources.
        output_path.mkdir(parents=True, exist_ok=True)
        
        with Progress() as progress:
            asyncio.run(
                pipeline.run_full_pipeline(
                    sources=[],
                    output_dir=str(output_path),
                    progress=progress,
                    max_workers=max_workers,
                    proxies=proxies,
                    timeout=timeout,
                )
            )
        
        # ===== STEP 5: Report success =====
        # If we reach this point without raising an exception, the retest succeeded.
        # Print success messages and let the function exit cleanly with code 0.
        click.echo("\n✓ Retest completed successfully!")
        click.echo(f"✓ Output files saved to: {output_path}")
    
    except Exception as e:
        # Catch any unexpected errors during pipeline execution or other operations
        # that aren't handled by the specific exception handlers above.
        # Note: sys.exit() raises SystemExit which is a BaseException, not Exception,
        # so this won't accidentally catch our intentional exits.
        click.echo(f"An error occurred: {e}", err=True)
        sys.exit(1)


def main():
    """Entry point for the CLI application."""
    cli()


if __name__ == "__main__":
    main()
