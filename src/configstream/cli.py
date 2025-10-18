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
    type=click.Path(dir_okay=False),  # Don't validate exists=True here
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

    This command reads a proxies.json file (typically from a previous merge run),
    re-tests each proxy for availability and latency, then generates updated
    output files. Useful for refreshing proxy status without re-fetching from sources.

    Examples:
        configstream retest --input output/proxies.json --output output/
        configstream retest --input output/proxies.json --max-workers 20 --timeout 15
    """
    # Set event loop policy for Windows compatibility
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    input_path = Path(input_file)
    output_path = Path(output_dir)

    try:
        # ===== STEP 1: Validate Input File Exists =====
        # Check if the input file exists. If not, provide clear error with exit code 2
        # (following Click's convention for parameter validation failures)
        if not input_path.exists():
            click.echo(
                f"Error: Path '{input_file}' does not exist.",
                err=True
            )
            sys.exit(2)

        # ===== STEP 2: Load and Parse JSON =====
        # Read the JSON file containing previously tested proxies
        try:
            with open(input_path, 'r') as f:
                proxies_data = json.load(f)
        except json.JSONDecodeError as e:
            # Catch JSON parsing errors and report them clearly
            # Extract the specific error message (e.g., "Expecting property name")
            error_msg = str(e)
            click.echo(
                f"Error: An error occurred: {error_msg}",
                err=True
            )
            sys.exit(1)
        except Exception as e:
            # Catch other file reading errors (permissions, encoding, etc.)
            click.echo(
                f"Error: An error occurred: {e}",
                err=True
            )
            sys.exit(1)

        # ===== STEP 3: Validate We Have Proxies =====
        # Check if the JSON file was empty (empty list [])
        # This is distinct from a file not existing—the file exists but has no proxies
        if not proxies_data or len(proxies_data) == 0:
            click.echo(
                "Error: No proxies found in the input file.",
                err=True
            )
            sys.exit(1)

        click.echo(f"✓ Loaded {len(proxies_data)} proxies from {input_file}")

        # ===== STEP 4: Reconstruct Proxy Objects =====
        # Convert the JSON data back into Proxy objects
        # This validates that the data structure is correct before testing
        proxies: list[Proxy] = []
        invalid_entries: list[tuple[int, str]] = []

        for index, proxy_data in enumerate(proxies_data, start=1):
            try:
                # Attempt to create a Proxy object from the JSON data
                # If required fields are missing or have wrong types, this raises TypeError
                proxy = Proxy(**proxy_data)
                proxies.append(proxy)
            except (TypeError, ValueError) as exc:
                # Track which entries failed and why
                invalid_entries.append((index, str(exc)))

        # If any proxies failed to load, report them but continue with valid ones
        if invalid_entries:
            click.echo(
                f"Warning: {len(invalid_entries)} invalid proxy definition(s) skipped",
                err=False
            )
            for index, error in invalid_entries[:5]:  # Show first 5 errors
                click.echo(f"  • Entry #{index}: {error}", err=False)
            if len(invalid_entries) > 5:
                click.echo(f"  • ... and {len(invalid_entries) - 5} more", err=False)

        if not proxies:
            click.echo(
                "Error: No valid proxies to retest.",
                err=True
            )
            sys.exit(1)

        click.echo(f"✓ Validated {len(proxies)} proxy definitions")

        # ===== STEP 5: Run Retest Pipeline =====
        # Execute the full pipeline with the loaded proxies
        # Pass empty sources list since we're retesting existing proxies, not fetching new ones
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

        # ===== STEP 6: Report Success =====
        # If we reach here without exceptions, the retest succeeded
        # Return cleanly (no explicit sys.exit(0)) to get exit code 0
        click.echo("\n✓ Retest completed successfully!")
        click.echo(f"✓ Output files saved to: {output_path}")

    except FileNotFoundError:
        # This shouldn't happen if input_path.exists() check passes,
        # but include it as a safety net for race conditions
        if ctx.get_parameter_source('input_file') == click.core.ParameterSource.DEFAULT:
            click.echo("Error: No proxies found in the input file.", err=True)
            sys.exit(1)
        else:
            click.echo(f"Error: Path '{input_file}' does not exist.", err=True)
            sys.exit(2)

    except Exception as e:
        # Catch any other unexpected errors during pipeline execution
        click.echo(
            f"Error: An error occurred: {e}",
            err=True
        )
        sys.exit(1)


def main():
    """Entry point for the CLI application."""
    cli()


if __name__ == "__main__":
    main()
