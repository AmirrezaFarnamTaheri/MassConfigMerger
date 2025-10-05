"""Functions for managing the sources list file.

This module provides a set of functions for interacting with the `sources.txt`
file, allowing users to list, add, and remove source URLs programmatically
instead of manually editing the file. It also includes handlers for the CLI
'sources' subcommand.
"""
from __future__ import annotations

import argparse
import ipaddress
import socket
from pathlib import Path
from typing import List
from urllib.parse import urlparse, urlunparse


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


def handle_list_sources(args: argparse.Namespace) -> None:
    """Handler for the 'sources list' command."""
    sources = list_sources(Path(args.sources_file))
    if sources:
        for source in sources:
            print(source)
    else:
        print("No sources found in the specified file.")


def _is_public_url(url: str) -> bool:
    """Check if the URL points to a public, non-reserved IP address."""
    try:
        hostname = urlparse(url).hostname
        if not hostname:
            return False
        ip = socket.gethostbyname(hostname)
        return not ipaddress.ip_address(ip).is_private
    except (socket.gaierror, ValueError):
        return False


def handle_add_source(args: argparse.Namespace) -> None:
    """Handler for the 'sources add' command."""
    parsed_url = urlparse(args.url)
    if not (parsed_url.scheme in {"http", "https"} and parsed_url.netloc):
        print(f"Invalid URL format: {args.url}")
        return
    if not _is_public_url(args.url):
        print(f"URL does not point to a public IP address: {args.url}")
        return

    if add_source(Path(args.sources_file), args.url):
        print(f"Source added: {args.url}")
    else:
        print(f"Source already exists: {args.url}")


def handle_remove_source(args: argparse.Namespace) -> None:
    """Handler for the 'sources remove' command."""
    parsed = urlparse(args.url)
    if not (parsed.scheme in {"http", "https"} and parsed.netloc):
        print(f"Invalid URL format: {args.url}")
        return
    # Normalize by removing fragments/query and ensuring lowercased scheme/host
    normalized = urlunparse(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "", "", "", "")
    )
    if remove_source(Path(args.sources_file), normalized):
        print(f"Source removed: {normalized}")
    else:
        print(f"Source not found: {normalized}")
