# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

"""Application services layer.

This module provides the core business logic of the ConfigStream application,
decoupled from the command-line interface. It orchestrates the main operations
such as fetching, merging, and retesting configurations.
"""
from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse

from . import pipeline, vpn_merger, vpn_retester
from .config import Settings
from .constants import RAW_SUBSCRIPTION_FILE_NAME


def _validate_and_format_url(url: str) -> str:
    """Validate and format the given URL."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    parsed = urlparse(url)
    if not all([parsed.scheme, parsed.netloc]):
        raise ValueError(f"Invalid URL format: {url}")
    return url


def _read_sources_from_file(sources_file: Path) -> list[str]:
    """Read all lines from the sources file."""
    if not sources_file.exists():
        return []
    return sources_file.read_text().splitlines()


def _write_sources_to_file(sources_file: Path, sources: list[str]) -> None:
    """Write a list of sources to the file, one per line."""
    sources_file.write_text("\n".join(sources) + "\n")


async def run_fetch_pipeline(
    cfg: Settings,
    sources_file: Path,
    channels_file: Path,
    last_hours: int,
    failure_threshold: int,
    prune: bool,
) -> None:
    """Run the aggregation pipeline to collect VPN configurations."""
    await pipeline.run_aggregation_pipeline(
        cfg,
        sources_file=sources_file,
        channels_file=channels_file,
        last_hours=last_hours,
        failure_threshold=failure_threshold,
        prune=prune,
    )


async def run_merge_pipeline(
    cfg: Settings, sources_file: Path, resume_file: Path | None
) -> None:
    """Run the VPN merger to test, sort, and merge configurations."""
    await vpn_merger.run_merger(cfg, sources_file=sources_file, resume_file=resume_file)


async def run_retest_pipeline(cfg: Settings, input_file: Path) -> None:
    """Re-test an existing subscription file."""
    await vpn_retester.run_retester(cfg, input_file=input_file)


async def run_full_pipeline(
    cfg: Settings,
    sources_file: Path,
    channels_file: Path,
    last_hours: int,
    failure_threshold: int,
    prune: bool,
) -> None:
    """Run the full pipeline: fetch, then merge and test."""
    aggregator_output_dir, _ = await pipeline.run_aggregation_pipeline(
        cfg,
        sources_file=sources_file,
        channels_file=channels_file,
        last_hours=last_hours,
        failure_threshold=failure_threshold,
        prune=prune,
    )
    resume_file = aggregator_output_dir / RAW_SUBSCRIPTION_FILE_NAME
    await vpn_merger.run_merger(cfg, sources_file=sources_file, resume_file=resume_file)


def list_sources(sources_file: Path) -> None:
    """List all sources from the sources file."""
    logging.info("Listing sources from: %s", sources_file)
    sources = _read_sources_from_file(sources_file)
    if not sources:
        print("No sources found.")
        return

    for i, source in enumerate(sources, 1):
        print(f"{i}. {source}")


def add_new_source(sources_file: Path, url: str) -> None:
    """Add a new source to the sources file."""
    try:
        validated_url = _validate_and_format_url(url)
        sources = _read_sources_from_file(sources_file)
        if validated_url in sources:
            print(f"Source already exists: {validated_url}")
            return

        sources.append(validated_url)
        _write_sources_to_file(sources_file, sources)
        print(f"Successfully added source: {validated_url}")

    except ValueError as e:
        print(f"Error: {e}")


def remove_existing_source(sources_file: Path, url: str) -> None:
    """Remove a source from the sources file."""
    sources = _read_sources_from_file(sources_file)
    original_count = len(sources)
    sources = [s for s in sources if s.strip() != url.strip()]

    if len(sources) < original_count:
        _write_sources_to_file(sources_file, sources)
        print(f"Successfully removed source: {url}")
    else:
        print(f"Source not found: {url}")
