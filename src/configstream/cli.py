from __future__ import annotations

import asyncio
import os
import sys
import gzip
import hashlib
from pathlib import Path

import click
import requests
from rich.progress import Progress

from . import pipeline
from .config import settings

# GeoIP Database URLs
GEOIP_COUNTRY_URL = "https://cdn.jsdelivr.net/npm/geolite2-country/GeoLite2-Country.mmdb.gz"
GEOIP_CITY_URL = "https://cdn.jsdelivr.net/gh/wp-statistics/GeoLite2-City@master/GeoLite2-City.mmdb.gz"
GEOIP_ASN_URL = "https://github.com/iplocate/ip-address-databases/raw/main/ip-to-asn/ip-to-asn.mmdb"

DATA_DIR = Path("data")
GEOIP_COUNTRY_DB_PATH = DATA_DIR / "GeoLite2-Country.mmdb"
GEOIP_CITY_DB_PATH = DATA_DIR / "GeoLite2-City.mmdb"
GEOIP_ASN_DB_PATH = DATA_DIR / "ip-to-asn.mmdb"


def _download_file(url: str, dest_path: Path, expected_hash: str | None = None) -> bool:
    """
    Download a file from URL to destination path with optional hash verification.
    """
    try:
        click.echo(f"Downloading from {url}...")
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            block_size = 8192
            with open(dest_path, "wb") as f:
                if total_size:
                    with Progress() as progress:
                        task = progress.add_task("[cyan]Downloading...", total=total_size)
                        for chunk in r.iter_content(chunk_size=block_size):
                            f.write(chunk)
                            progress.update(task, advance=len(chunk))
                else:
                    for chunk in r.iter_content(chunk_size=block_size):
                        f.write(chunk)

        # Verify hash if provided
        if expected_hash:
            with open(dest_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
                if file_hash != expected_hash:
                    click.echo(f"✗ Hash mismatch! Expected {expected_hash}, got {file_hash}", err=True)
                    dest_path.unlink(missing_ok=True)
                    return False

        click.echo(f"✓ Downloaded successfully: {dest_path.name}")
        return True
    except requests.RequestException as e:
        click.echo(f"✗ Error downloading from {url}: {e}", err=True)
        dest_path.unlink(missing_ok=True)
        return False
    except Exception as e:
        click.echo(f"✗ An unexpected error occurred: {e}", err=True)
        dest_path.unlink(missing_ok=True)
        return False


def download_geoip_dbs():
    """Download and extract GeoIP databases if they don't exist."""
    DATA_DIR.mkdir(exist_ok=True)

    # Download Country DB
    if not os.path.exists(GEOIP_COUNTRY_DB_PATH):
        click.echo("GeoIP Country database not found, downloading...")
        gz_path = DATA_DIR / "GeoLite2-Country.mmdb.gz"

        if _download_file(GEOIP_COUNTRY_URL, gz_path):
            try:
                with gzip.open(gz_path, "rb") as f_in:
                    with open(GEOIP_COUNTRY_DB_PATH, "wb") as f_out:
                        f_out.write(f_in.read())
                # Basic sanity check to ensure extraction produced data
                if os.path.getsize(GEOIP_COUNTRY_DB_PATH) == 0:
                    click.echo("✗ Extracted Country database is empty, aborting.", err=True)
                    if os.path.exists(GEOIP_COUNTRY_DB_PATH):
                        os.remove(GEOIP_COUNTRY_DB_PATH)
                    sys.exit(1)
                click.echo("✓ GeoIP Country database extracted successfully")
            except gzip.BadGzipFile as e:
                click.echo(f"✗ Error decompressing Country database: {e}", err=True)
                sys.exit(1)
            finally:
                # Only remove archive if we have a valid non-empty output
                if os.path.exists(GEOIP_COUNTRY_DB_PATH) and os.path.getsize(GEOIP_COUNTRY_DB_PATH) > 0:
                    if os.path.exists(gz_path):
                        gz_path.unlink()
        else:
            sys.exit(1)

    # Download City DB
    if not GEOIP_CITY_DB_PATH.exists():
        click.echo("GeoIP City database not found, downloading...")
        gz_path = DATA_DIR / "GeoLite2-City.mmdb.gz"
        tmp_city_path = DATA_DIR / "GeoLite2-City.mmdb.tmp"

        if _download_file(GEOIP_CITY_URL, gz_path):
            try:
                with gzip.open(gz_path, "rb") as f_in, open(tmp_city_path, "wb") as f_out:
                    f_out.write(f_in.read())
                tmp_city_path.replace(GEOIP_CITY_DB_PATH)
                click.echo("✓ GeoIP City database extracted successfully")
            except gzip.BadGzipFile as e:
                click.echo(f"✗ Error decompressing City database: {e}", err=True)
                click.echo("⚠ Warning: City database decompression failed; proceeding without City DB.")
                tmp_city_path.unlink(missing_ok=True)
            except Exception as e:
                click.echo(f"✗ Error writing City database: {e}", err=True)
                tmp_city_path.unlink(missing_ok=True)
            finally:
                if gz_path.exists():
                    gz_path.unlink()
        else:
            click.echo("⚠ Warning: City database download failed; proceeding without City DB.")

    # Download ASN DB
    if not os.path.exists(GEOIP_ASN_DB_PATH):
        click.echo("GeoIP ASN database not found, downloading...")
        if not _download_file(GEOIP_ASN_URL, GEOIP_ASN_DB_PATH):
            sys.exit(1)
        click.echo("✓ GeoIP ASN database downloaded successfully")


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
    download_geoip_dbs()

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
    click.echo("Updating GeoIP databases...")

    # Remove existing databases
    for db_path in [GEOIP_COUNTRY_DB_PATH, GEOIP_CITY_DB_PATH, GEOIP_ASN_DB_PATH]:
        if os.path.exists(db_path):
            db_path.unlink()
            click.echo(f"✓ Removed old database: {db_path.name}")

    # Download fresh databases
    download_geoip_dbs()

    click.echo("✓ All databases updated successfully!")


if __name__ == "__main__":
    main()
