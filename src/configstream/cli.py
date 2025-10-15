from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from rich.progress import Progress

import gzip
import os
import shutil

import requests

from . import pipeline
from .config import settings

GEOIP_URL = "https://cdn.jsdelivr.net/npm/geolite2-country/GeoLite2-Country.mmdb.gz"
DATA_DIR = Path("data")
GEOIP_DB_PATH = DATA_DIR / "GeoLite2-Country.mmdb"


def download_geoip_db():
    """Downloads and extracts the GeoLite2 Country database if it doesn't exist."""
    if GEOIP_DB_PATH.exists():
        return

    click.echo("GeoIP database not found, downloading...")
    DATA_DIR.mkdir(exist_ok=True)

    gz_path = DATA_DIR / "GeoLite2-Country.mmdb.gz"

    try:
        with requests.get(GEOIP_URL, stream=True) as r:
            r.raise_for_status()
            with open(gz_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        with gzip.open(gz_path, "rb") as f_in:
            with open(GEOIP_DB_PATH, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        click.echo("GeoIP database downloaded successfully.")
    except (requests.exceptions.RequestException, gzip.BadGzipFile) as e:
        click.echo(f"Error downloading GeoIP database: {e}", err=True)
        sys.exit(1)
    finally:
        if gz_path.exists():
            gz_path.unlink()


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
    required=True,
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
@click.option(
    "--max-proxies",
    "max_proxies",
    default=None,
    help="The maximum number of proxies to test.",
    type=int,
)
@click.option(
    "--country",
    "country",
    default=None,
    help="Filter proxies by country code (e.g., US, DE).",
    type=str,
)
def merge(sources_file: str, output_dir: str, max_proxies: int | None, country: str | None):
    """
    Run the full pipeline: fetch from sources, test proxies, and generate outputs.
    """
    download_geoip_db()

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        sources = Path(sources_file).read_text().splitlines()
        sources = [s.strip() for s in sources if s.strip() and not s.startswith("#")]
        if not sources:
            click.echo("No sources found in the specified file.", err=True)
            return

        with Progress() as progress:
            asyncio.run(pipeline.run_full_pipeline(sources, output_dir, progress, max_proxies=max_proxies, country=country))

    except FileNotFoundError:
        click.echo(f"Error: The sources file was not found at '{sources_file}'", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()