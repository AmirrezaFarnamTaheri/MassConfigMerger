from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import Field

from .base import BaseConfig


class ProcessingSettings(BaseConfig):
    """Settings for controlling the processing, sorting, and testing of configurations."""

    sort_by: Literal["latency", "reliability", "proximity"] = Field(
        "latency",
        description="Method for sorting configs ('latency', 'reliability', or 'proximity').",
    )
    proximity_latitude: Optional[float] = Field(
        None, description="Latitude for proximity sorting."
    )
    proximity_longitude: Optional[float] = Field(
        None, description="Longitude for proximity sorting."
    )
    enable_sorting: bool = Field(
        True, description="Whether to sort configs by performance."
    )
    enable_url_testing: bool = Field(
        True, description="Whether to enable real-time connectivity testing of configs."
    )
    top_n: int = Field(
        0, description="Keep only the top N best configs after sorting. 0 to keep all."
    )
    shuffle_sources: bool = Field(
        False, description="Whether to shuffle the list of sources before fetching."
    )
    max_configs_per_source: int = Field(
        75000, description="Maximum number of configs to parse from a single source."
    )
    stop_after_found: int = Field(
        0, description="Stop processing after finding N unique configs. 0 to disable."
    )
    save_every: int = Field(
        1000,
        description="Save intermediate results every N configs found. 0 to disable.",
    )
    cumulative_batches: bool = Field(
        False,
        description="If true, each saved batch is a cumulative collection of all configs found so far.",
    )
    strict_batch: bool = Field(
        True,
        description="If true, save batches exactly every 'save_every' configs.",
    )
    mux_concurrency: int = Field(8, description="Mux concurrency for supported URI configs.")
    smux_streams: int = Field(4, description="Smux streams for supported URI configs.")
    geoip_db: Optional[Path] = Field(
        None, description="Path to the GeoLite2 Country MMDB file for GeoIP lookups."
    )
    resume_file: Optional[Path] = Field(
        None, description="Path to a raw or base64 subscription file to resume/retest."
    )
    max_retries: int = Field(
        3, description="Maximum retry attempts for fetching subscription sources in the merger."
    )