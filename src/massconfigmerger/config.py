"""Application configuration models and loading logic.

This module defines the Pydantic models for all application settings,
structured into logical groups. It also provides a custom YAML loader
and a `load_config` function to create a populated `Settings` object,
loading from a YAML file and environment variables.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Literal

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from .core.file_utils import find_project_root


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """A settings source that loads variables from a YAML file."""

    def __init__(self, settings_cls: Type[BaseSettings], yaml_file: Optional[Path]):
        super().__init__(settings_cls)
        self.yaml_file = yaml_file

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str] | None:
        if not self.yaml_file or not self.yaml_file.exists():
            return None
        try:
            yaml_data = yaml.safe_load(self.yaml_file.read_text()) or {}
            field_value = yaml_data.get(field_name)
            return field_value, field_name
        except (yaml.YAMLError, IOError):
            return None

    def __call__(self) -> dict[str, Any]:
        if not self.yaml_file or not self.yaml_file.exists():
            return {}
        try:
            return yaml.safe_load(self.yaml_file.read_text()) or {}
        except (yaml.YAMLError, IOError):
            return {}


class TelegramSettings(BaseModel):
    """Settings for Telegram integration."""

    api_id: Optional[int] = Field(None, description="Your Telegram API ID.")
    api_hash: Optional[str] = Field(None, description="Your Telegram API hash.")
    bot_token: Optional[str] = Field(None, description="Your Telegram bot token for bot mode.")
    allowed_user_ids: List[int] = Field(
        default_factory=list,
        description="List of Telegram user IDs allowed to interact with the bot.",
    )
    session_path: str = Field("user.session", description="Path to the Telethon session file.")

    @field_validator("allowed_user_ids", mode="before")
    @classmethod
    def _parse_allowed_ids(cls, value):
        if isinstance(value, str):
            try:
                return [int(v) for v in re.split(r"[\s,]+", value.strip()) if v]
            except ValueError as exc:
                raise ValueError("allowed_user_ids must be a list of integers") from exc
        if isinstance(value, int):
            return [value]
        return value


class NetworkSettings(BaseModel):
    """Settings related to network requests."""

    request_timeout: int = Field(10, description="Timeout for HTTP requests in seconds.")
    concurrent_limit: int = Field(20, description="Maximum number of concurrent HTTP requests.")
    retry_attempts: int = Field(3, description="Number of retry attempts for failed HTTP requests.")
    retry_base_delay: float = Field(1.0, description="Base delay for exponential backoff between retries.")
    connect_timeout: float = Field(3.0, description="Connection timeout for testing configs in seconds.")
    http_proxy: Optional[str] = Field(None, alias="HTTP_PROXY", description="URL for an HTTP proxy.")
    socks_proxy: Optional[str] = Field(None, alias="SOCKS_PROXY", description="URL for a SOCKS proxy.")
    headers: Dict[str, str] = Field(
        default={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        },
        description="Default headers for HTTP requests.",
    )


class FilteringSettings(BaseModel):
    """Settings for filtering configurations."""

    fetch_protocols: List[str] = Field(default_factory=list, description="List of VPN protocols to fetch from sources.")
    include_patterns: List[str] = Field(default_factory=list, description="List of regex patterns to include configs.")
    exclude_patterns: List[str] = Field(default_factory=list, description="List of regex patterns to exclude configs.")
    merge_include_protocols: Set[str] = Field(
        default={"SHADOWSOCKS", "SHADOWSOCKSR", "TROJAN", "REALITY", "VMESS", "VLESS", "HYSTERIA", "HYSTERIA2", "TUIC", "NAIVE", "JUICITY", "WIREGUARD", "SHADOWTLS", "BROOK"},
        description="Set of protocols to include in the final merged output.",
    )
    merge_exclude_protocols: Set[str] = Field(default={"OTHER"}, description="Set of protocols to exclude from the final merged output.")
    include_countries: Optional[Set[str]] = Field(None, description="Set of ISO country codes to include (requires GeoIP).")
    exclude_countries: Optional[Set[str]] = Field(None, description="Set of ISO country codes to exclude (requires GeoIP).")
    max_ping_ms: Optional[int] = Field(1000, description="Maximum acceptable ping in milliseconds.")
    tls_fragment: Optional[str] = Field(None, description="Filter configs to only include those with a specific TLS fragment.")
    valid_prefixes: Tuple[str, ...] = Field(
        default=(
            "vmess://", "vless://", "reality://", "ss://", "ssr://", "trojan://", "hy2://",
            "hysteria://", "hysteria2://", "tuic://", "shadowtls://", "wireguard://",
            "socks://", "socks4://", "socks5://", "http://", "https://", "grpc://",
            "ws://", "wss://", "tcp://", "kcp://", "quic://", "h2://",
        ),
        description="Tuple of valid URI prefixes for VPN configs.",
    )


class OutputSettings(BaseModel):
    """Settings for output files and formats."""

    output_dir: str = Field("output", description="Directory to save output files.")
    log_dir: str = Field("logs", description="Directory to save log files.")
    log_file: Optional[str] = Field(None, description="Path to a file for logging output.")
    history_file: str = Field("proxy_history.json", description="File to store proxy connection history.")
    write_base64: bool = Field(True, description="Whether to write a base64-encoded subscription file.")
    write_singbox: bool = Field(True, description="Whether to write a sing-box compatible subscription file.")
    write_clash: bool = Field(True, description="Whether to write a Clash compatible subscription file.")
    write_csv: bool = Field(True, description="Whether to write a detailed CSV report.")
    write_html: bool = Field(False, description="Whether to write an HTML report.")
    write_clash_proxies: bool = Field(True, description="Whether to write a simple Clash proxies file.")
    surge_file: Optional[str] = Field(None, description="Filename for Surge output configuration.")
    qx_file: Optional[str] = Field(None, description="Filename for Quantumult X output configuration.")
    xyz_file: Optional[str] = Field(None, description="Filename for XYZ format output configuration.")
    github_token: Optional[str] = Field(None, description="GitHub token for uploading gists.")


class ProcessingSettings(BaseModel):
    """Settings for processing and sorting configurations."""

    sort_by: Literal["latency", "reliability"] = Field("latency", description="Method for sorting configs ('latency' or 'reliability').")
    enable_sorting: bool = Field(True, description="Whether to sort configs by performance.")
    enable_url_testing: bool = Field(True, description="Whether to enable real-time connectivity testing of configs.")
    top_n: int = Field(0, description="Keep only the top N best configs after sorting. 0 to keep all.")
    shuffle_sources: bool = Field(False, description="Whether to shuffle the list of sources before fetching.")
    max_configs_per_source: int = Field(75000, description="Maximum number of configs to parse from a single source.")
    stop_after_found: int = Field(0, description="Stop processing after finding N unique configs. 0 to disable.")
    save_every: int = Field(1000, description="Save intermediate results every N configs found. 0 to disable.")
    cumulative_batches: bool = Field(False, description="If true, each saved batch is a cumulative collection of all configs found so far.")
    strict_batch: bool = Field(True, description="If true, save batches exactly every 'save_every' configs.")
    mux_concurrency: int = Field(8, description="Mux concurrency for supported URI configs.")
    smux_streams: int = Field(4, description="Smux streams for supported URI configs.")
    geoip_db: Optional[str] = Field(None, description="Path to the GeoLite2 Country MMDB file for GeoIP lookups.")
    resume_file: Optional[str] = Field(None, description="Path to a raw or base64 subscription file to resume/retest.")
    max_retries: int = Field(3, description="Maximum retry attempts for fetching subscription sources in the merger.")


class Settings(BaseSettings):
    """Main application configuration."""

    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    network: NetworkSettings = Field(default_factory=NetworkSettings)
    filtering: FilteringSettings = Field(default_factory=FilteringSettings)
    output: OutputSettings = Field(default_factory=OutputSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)

    config_file: Optional[Path] = Field(default=None, exclude=True)

    model_config = SettingsConfigDict(
        env_prefix="", case_sensitive=False, env_nested_delimiter="__"
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
        config_file = init_settings.init_kwargs.get("config_file")
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file=config_file),
            file_secret_settings,
        )


def load_config(path: Path | None = None) -> Settings:
    """Load configuration from a file and environment variables."""
    config_file = path
    if config_file is None:
        try:
            project_root = find_project_root()
            default_config_path = project_root / "config.yaml"
            if default_config_path.exists():
                config_file = default_config_path
        except FileNotFoundError:
            logging.warning(
                "Could not find project root marker 'pyproject.toml'. "
                "Default 'config.yaml' will not be loaded."
            )
    return Settings(config_file=config_file)