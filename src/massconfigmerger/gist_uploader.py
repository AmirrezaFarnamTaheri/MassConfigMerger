"""Handles uploading files to GitHub Gists.

This module provides asynchronous functions to upload generated output files
to GitHub as private Gists and to write the resulting URLs to a local file
for easy access.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

import aiohttp

from .constants import UPLOAD_LINKS_FILE_NAME


class GistUploadError(Exception):
    """Custom exception for Gist upload failures."""
    pass


async def upload_files_to_gist(
    paths: List[Path], token: str, *, base_url: str = "https://api.github.com"
) -> Dict[str, str]:
    """Upload files as separate private gists and return name->raw_url mapping."""

    if not token:
        raise ValueError("GitHub token is required to upload gists")

    parsed = urlparse(base_url)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise ValueError(f"Invalid base_url: {base_url}")

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    result: Dict[str, str] = {}
    base = base_url.rstrip("/") + "/gists"
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        for path in paths:
            if not path.exists() or not path.is_file():
                raise GistUploadError(f"Gist upload source is not a file: {path}")
            content = path.read_text(encoding="utf-8")
            payload = {
                "files": {path.name: {"content": content}},
                "public": False,
                "description": "MassConfigMerger output",
            }
            async with session.post(base, json=payload) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise GistUploadError(f"Gist upload failed for {path.name}: {resp.status} {body}")
                try:
                    data = await resp.json(content_type=None)
                except Exception as e:
                    body = await resp.text()
                    raise GistUploadError(f"Failed to parse Gist response for {path.name}: {body}") from e
                try:
                    raw = data["files"][path.name]["raw_url"]
                except (KeyError, TypeError):
                    raise GistUploadError(f"Unexpected Gist response for {path.name}: {data}")
                result[path.name] = raw
    return result


def write_upload_links(links: Dict[str, str], output_dir: Path) -> Path:
    """Write uploaded file links to output_dir/upload_links.txt and return the path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / UPLOAD_LINKS_FILE_NAME
    tmp = dest.with_suffix(".tmp")
    tmp.write_text("\n".join(f"{k}: {v}" for k, v in links.items()), encoding="utf-8")
    tmp.replace(dest)
    return dest
