"""Functions for managing the sources list file.

This module provides a set of functions for interacting with the `sources.txt`
file, allowing users to list, add, and remove source URLs programmatically
instead of manually editing the file.
"""
from __future__ import annotations

from pathlib import Path
from typing import List


def list_sources(sources_file: Path) -> List[str]:
    """
    Read and return all source URLs from the specified file.

    Args:
        sources_file: The path to the sources file.

    Returns:
        A list of source URLs.
    """
    if not sources_file.exists():
        return []
    with sources_file.open("r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def add_source(sources_file: Path, url: str) -> bool:
    """
    Add a new source URL to the sources file.

    This function will not add the URL if it already exists in the file.

    Args:
        sources_file: The path to the sources file.
        url: The URL to add.

    Returns:
        True if the URL was added, False if it already existed.
    """
    sources = list_sources(sources_file)
    if url in sources:
        return False

    with sources_file.open("a", encoding="utf-8") as f:
        f.write(f"{url}\n")
    return True


def remove_source(sources_file: Path, url: str) -> bool:
    """
    Remove a source URL from the sources file.

    Args:
        sources_file: The path to the sources file.
        url: The URL to remove.

    Returns:
        True if the URL was found and removed, False otherwise.
    """
    sources = list_sources(sources_file)
    if url not in sources:
        return False

    updated_sources = [s for s in sources if s != url]
    with sources_file.open("w", encoding="utf-8") as f:
        for s in updated_sources:
            f.write(f"{s}\n")
    return True