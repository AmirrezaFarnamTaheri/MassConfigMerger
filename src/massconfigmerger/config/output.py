from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field

from ..constants import HISTORY_DB_FILE_NAME
from .base import BaseConfig


class OutputSettings(BaseConfig):
    """Settings for controlling the generated output files and formats."""

    output_dir: Path = Field(
        Path("output"), description="Directory to save all output files."
    )
    log_dir: Path = Field(Path("logs"), description="Directory to save log files.")
    log_file: Optional[Path] = Field(
        None, description="Path to a specific file for logging, instead of a directory."
    )
    history_db_file: Path = Field(
        Path(HISTORY_DB_FILE_NAME),
        description="SQLite database file to store proxy connection history for reliability scoring.",
    )
    write_base64: bool = Field(
        True, description="Whether to write a base64-encoded subscription file."
    )
    write_singbox: bool = Field(
        True, description="Whether to write a sing-box compatible subscription file."
    )
    write_clash: bool = Field(
        True, description="Whether to write a Clash compatible subscription file."
    )
    write_csv: bool = Field(True, description="Whether to write a detailed CSV report.")
    write_html: bool = Field(False, description="Whether to write an HTML report.")
    write_clash_proxies: bool = Field(
        True, description="Whether to write a simple Clash proxies-only file."
    )
    surge_file: Optional[Path] = Field(
        None, description="Filename for Surge output configuration."
    )
    qx_file: Optional[Path] = Field(
        None, description="Filename for Quantumult X output configuration."
    )
    xyz_file: Optional[Path] = Field(
        None, description="Filename for XYZ format output configuration."
    )
    upload_gist: bool = Field(
        False, description="Whether to upload output files to a GitHub Gist."
    )
    github_token: Optional[str] = Field(
        None, description="GitHub personal access token for uploading gists."
    )