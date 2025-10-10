"""Application configuration models for ConfigStream.

This module defines the data structures for all application settings using
Pydantic's `BaseSettings` and `BaseModel`. The settings are organized into
logical groups (e.g., `NetworkSettings`, `FilteringSettings`) and then
nested within a main `Settings` class. This structure allows for a clean
and type-safe way to manage configuration that can be loaded from various
sources, including YAML files and environment variables.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Type

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from .constants import CONFIG_FILE_NAME, HISTORY_DB_FILE_NAME
from .core.file_utils import find_project_root


class YamlConfigSettingsSource:
    """
    A Pydantic settings source that loads variables from a YAML file.
    """

    def __init__(self, yaml_file: Path | None):
        self._yaml_file = yaml_file
        self._data: dict[str, Any] | None = None

    def __call__(self) -> dict[str, Any]:
        if self._data is None:
            if self._yaml_file and self._yaml_file.exists():
                try:
                    self._data = yaml.safe_load(
                        self._yaml_file.read_text()) or {}
                except (yaml.YAMLError, IOError) as e:
                    logging.warning(
                        "Could not read or parse YAML config from %s: %s",
                        self._yaml_file,
                        e,
                    )
                    self._data = {}
            else:
                self._data = {}
        return self._data


class TelegramSettings(BaseModel):
    """Settings for Telegram integration."""

    api_id: Optional[int] = Field(
        None, description="Your Telegram API ID from my.telegram.org.")
    api_hash: Optional[str] = Field(
        None, description="Your Telegram API hash from my.telegram.org.")
    session_path: Path = Field(
        "user.session", description="Path to the Telethon session file."
    )
    allowed_user_ids: Optional[List[int]] = Field(
        None, description="Optional list of user IDs allowed to interact with the bot."
    )

    @field_validator("allowed_user_ids", mode="before")
    def _parse_user_ids(cls, v: Any) -> Optional[List[int]]:
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return [int(uid.strip()) for uid in v.split(",") if uid.strip()]
            except ValueError:
                raise ValueError(
                    "allowed_user_ids must be a string of comma-separated integers"
                )
        raise ValueError(
            "allowed_user_ids must be a list or a comma-separated string of integers"
        )


class NetworkSettings(BaseModel):
    """Settings related to network requests, timeouts, and proxies."""

    request_timeout: int = Field(
        10, description="General timeout for HTTP requests in seconds.")
    concurrent_limit: int = Field(
        20, description="Maximum number of concurrent HTTP requests."
    )
    connection_limit: int = Field(
        100,
        description="Maximum number of simultaneous TCP connections in the pool. 0 for unlimited.",
    )
    retry_attempts: int = Field(
        3, description="Number of retry attempts for failed HTTP requests."
    )
    retry_base_delay: float = Field(
        1.0, description="Base delay for exponential backoff between retries."
    )
    retry_jitter: float = Field(
        0.5, description="Amount of random jitter to apply to retry delays (0 to 1)."
    )
    connect_timeout: float = Field(
        3.0, description="Connection timeout for testing individual VPN configs in seconds."
    )
    http_proxy: Optional[str] = Field(
        None, alias="HTTP_PROXY", description="URL for an HTTP proxy (e.g., 'http://user:pass@host:port')."
    )
    socks_proxy: Optional[str] = Field(
        None, alias="SOCKS_PROXY", description="URL for a SOCKS proxy (e.g., 'socks5://user:pass@host:port')."
    )
    headers: Dict[str, str] = Field(
        default={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        },
        description="Default headers to use for all HTTP requests.",
    )


class FilteringSettings(BaseModel):
    """Settings for filtering configurations at different stages of the pipeline."""

    fetch_protocols: List[str] = Field(
        default_factory=list,
        description="List of VPN protocols to fetch from sources (e.g., ['VLESS', 'SS']).",
    )
    include_patterns: Optional[List[str]] = Field(
        None, description="List of regex patterns to include configs by name."
    )
    exclude_patterns: Optional[List[str]] = Field(
        None, description="List of regex patterns to exclude configs by name."
    )
    merge_include_protocols: Set[str] = Field(
        default={"SHADOWSOCKS", "SHADOWSOCKSR", "TROJAN", "REALITY", "VMESS", "VLESS",
                 "HYSTERIA", "HYSTERIA2", "TUIC", "NAIVE", "JUICITY", "WIREGUARD", "SHADOWTLS", "BROOK"},
        description="Set of protocols to include in the final merged output.",
    )
    merge_exclude_protocols: Set[str] = Field(
        default={"OTHER"},
        description="Set of protocols to exclude from the final merged output.",
    )
    include_isps: Optional[Set[str]] = Field(
        None, description="Set of ISP names to include (e.g., {'Google', 'Amazon'}). Requires GeoIP."
    )
    exclude_isps: Optional[Set[str]] = Field(
        None, description="Set of ISP names to exclude. Requires GeoIP."
    )
    max_ping_ms: Optional[int] = Field(
        1000, description="Maximum acceptable ping in milliseconds for a config to be included."
    )


class OutputSettings(BaseModel):
    """Settings for controlling the generated output files and formats."""

    output_dir: Path = Field(
        Path("output"), description="Directory to save all output files."
    )
    log_file: Optional[Path] = Field(
        None, description="Path to a specific file for logging, instead of a directory."
    )

    @field_validator(
        "output_dir", "log_file", "history_db_file", "surge_file", "qx_file", mode="before"
    )
    @classmethod
    def _validate_path_is_safe(cls, v: Any) -> Path | None:
        """Ensure user-provided paths are not absolute and do not contain '..'.

        This is a security measure to prevent path traversal attacks.
        """
        if v is None:
            return None

        # Normalize input
        path_str = str(v).strip()
        p = Path(path_str)

        # Reject absolute paths and parent traversal anywhere in parts
        if p.is_absolute() or ".." in p.parts:
            raise ValueError(
                f"Path cannot be absolute or contain '..': {path_str}")

        # Allow drive letters if not absolute (e.g., 'C:folder' on Windows)
        return p

    history_db_file: Path = Field(
        Path(HISTORY_DB_FILE_NAME),
        description="SQLite database file to store proxy connection history for reliability scoring.",
    )
    write_base64: bool = Field(
        True, description="Whether to write a base64-encoded subscription file."
    )
    write_clash: bool = Field(
        True, description="Whether to write a Clash compatible subscription file."
    )
    write_csv: bool = Field(
        True, description="Whether to write a detailed CSV report.")
    write_html: bool = Field(
        False, description="Whether to write an HTML report.")
    write_clash_proxies: bool = Field(
        True, description="Whether to write a simple Clash proxies-only file."
    )
    surge_file: Optional[Path] = Field(
        None, description="Filename for Surge output configuration."
    )
    qx_file: Optional[Path] = Field(
        None, description="Filename for Quantumult X output configuration."
    )
    current_results_file: Path = Field(
        Path("data/current_results.json"),
        description="File to store the latest test results for the dashboard."
    )
    history_file: Path = Field(
        Path("data/history.jsonl"),
        description="File to store the historical test results for the dashboard."
    )


class TestingSettings(BaseModel):
    """Settings for advanced testing features."""
    enable_advanced_tests: bool = Field(False, description="Enable advanced tests like network quality and bandwidth.")
    advanced_test_top_n: int = Field(10, description="Number of top nodes to run advanced tests on.")
    test_bandwidth: bool = Field(False, description="Enable bandwidth testing (can be slow).")
    test_network_quality: bool = Field(True, description="Enable network quality (jitter, packet loss) testing.")


class SecuritySettings(BaseModel):
    """Settings for security-related features like blocklist checking."""

    apivoid_api_key: Optional[str] = Field(
        None, description="API key for APIVoid IP Reputation API."
    )
    blocklist_detection_threshold: int = Field(
        1,
        description="Number of blacklist detections required to consider an IP malicious. 0 to disable.",
    )
    api_key: Optional[str] = Field(
        None,
        description="Optional API key to protect API endpoints. If set, it must be provided in the 'X-API-Key' header.",
    )


class ProcessingSettings(BaseModel):
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
    mux_concurrency: int = Field(
        8, description="Mux concurrency for supported URI configs.")
    smux_streams: int = Field(
        4, description="Smux streams for supported URI configs.")
    geoip_db: Optional[Path] = Field(
        None, description="Path to the GeoLite2 Country MMDB file for GeoIP lookups."
    )
    resume_file: Optional[Path] = Field(
        None, description="Path to a raw or base64 subscription file to resume/retest."
    )


class SourcesSettings(BaseModel):
    """Settings for managing subscription sources."""

    sources_file: Path = Field(
        "sources.txt", description="File containing subscription source URLs."
    )


class Settings(BaseSettings):
    """
    Main application configuration model.
    """

    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    network: NetworkSettings = Field(default_factory=NetworkSettings)
    filtering: FilteringSettings = Field(default_factory=FilteringSettings)
    output: OutputSettings = Field(default_factory=OutputSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    testing: TestingSettings = Field(default_factory=TestingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    sources: SourcesSettings = Field(default_factory=SourcesSettings)

    config_file: Optional[Path] = Field(default=None, exclude=True)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_prefix="CONFIGSTREAM_",
        case_sensitive=False,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Determine the config file path from init_settings if provided
        config_file_path = init_settings.init_kwargs.get("config_file")

        return (
            init_settings,
            YamlConfigSettingsSource(config_file_path),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )


def load_config(path: Path | None = None) -> Settings:
    """
    Load application settings from a YAML file and environment variables.
    """
    config_file = path
    if config_file is None:
        try:
            project_root = find_project_root()
            default_config_path = project_root / CONFIG_FILE_NAME
            if default_config_path.exists():
                config_file = default_config_path
        except FileNotFoundError:
            logging.warning(
                "Could not find project root marker 'pyproject.toml'. "
                "Default '%s' will not be loaded.",
                CONFIG_FILE_NAME,
            )
    return Settings(config_file=config_file)
