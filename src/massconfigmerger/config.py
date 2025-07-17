from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import os
import re

import yaml
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config.yaml"


class Settings(BaseSettings):
    """Application configuration loaded from YAML with env overrides."""

    # Telegram / aggregator settings
    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    allowed_user_ids: List[int] = []
    session_path: str = "user.session"

    protocols: List[str] = []
    exclude_patterns: List[str] = []
    include_patterns: List[str] = Field(default_factory=list)
    output_dir: str = "output"
    log_dir: str = "logs"
    request_timeout: int = 10
    concurrent_limit: int = 20
    retry_attempts: int = 3
    retry_base_delay: float = 1.0
    write_base64: bool = True
    write_singbox: bool = True
    write_clash: bool = True
    HTTP_PROXY: Optional[str] = None
    SOCKS_PROXY: Optional[str] = None
    github_token: Optional[str] = None

    # Merger settings
    headers: Dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }
    connect_timeout: float = 3.0
    max_retries: int = 3
    max_configs_per_source: int = 75000
    valid_prefixes: Tuple[str, ...] = (
        "vmess://",
        "vless://",
        "reality://",
        "ss://",
        "ssr://",
        "trojan://",
        "hy2://",
        "hysteria://",
        "hysteria2://",
        "tuic://",
        "shadowtls://",
        "wireguard://",
        "socks://",
        "socks4://",
        "socks5://",
        "http://",
        "https://",
        "grpc://",
        "ws://",
        "wss://",
        "tcp://",
        "kcp://",
        "quic://",
        "h2://",
    )
    enable_url_testing: bool = True
    enable_sorting: bool = True
    save_every: int = 1000
    stop_after_found: int = 0
    top_n: int = 0
    tls_fragment: Optional[str] = None
    include_protocols: Optional[Set[str]] = {
        "SHADOWSOCKS",
        "SHADOWSOCKSR",
        "TROJAN",
        "REALITY",
        "VMESS",
        "VLESS",
        "HYSTERIA",
        "HYSTERIA2",
        "TUIC",
        "NAIVE",
        "JUICITY",
        "WIREGUARD",
        "SHADOWTLS",
        "BROOK",
    }
    exclude_protocols: Optional[Set[str]] = {"OTHER"}
    resume_file: Optional[str] = None
    max_ping_ms: Optional[int] = 1000
    log_file: Optional[str] = None
    cumulative_batches: bool = False
    strict_batch: bool = True
    shuffle_sources: bool = False
    write_csv: bool = True
    write_html: bool = False
    write_clash_proxies: bool = True
    surge_file: Optional[str] = None
    qx_file: Optional[str] = None
    xyz_file: Optional[str] = None
    mux_concurrency: int = 8
    smux_streams: int = 4
    geoip_db: Optional[str] = None
    include_countries: Optional[Set[str]] = None
    exclude_countries: Optional[Set[str]] = None
    history_file: str = "proxy_history.json"
    sort_by: str = "latency"

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    @classmethod
    def _parse_allowed_ids(cls, value):
        if isinstance(value, str):
            try:
                return [int(v) for v in re.split(r"[ ,]+", value.strip()) if v]
            except ValueError as exc:
                raise ValueError("allowed_user_ids must be a list of integers") from exc
        if isinstance(value, int):
            return [value]
        return value

    @field_validator("allowed_user_ids", mode="before")
    @classmethod
    def validate_allowed_ids(cls, value):
        return cls._parse_allowed_ids(value)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return env_settings, init_settings, dotenv_settings, file_secret_settings

def load_config(path: Path | None = None, *, defaults: dict | None = None) -> Settings:
    """Load configuration from ``path`` or the repository root."""

    if path is None:
        path = DEFAULT_CONFIG_PATH

    try:
        data = yaml.safe_load(Path(path).read_text()) or {}
    except FileNotFoundError as exc:
        raise ValueError(f"Config file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc

    if defaults:
        for k, v in defaults.items():
            data.setdefault(k, v)

    if "allowed_user_ids" in data:
        try:
            data["allowed_user_ids"] = [int(i) for i in data["allowed_user_ids"]]
        except Exception as exc:
            raise ValueError("allowed_user_ids must be a list of integers") from exc

    env_raw = {
        field: os.environ[field.upper()]
        for field in Settings.model_fields
        if os.getenv(field.upper()) is not None
    }
    if env_raw:
        parsed = {}
        for k, v in env_raw.items():
            try:
                parsed[k] = yaml.safe_load(v)
            except Exception:
                parsed[k] = v
        backup = {k.upper(): os.environ[k.upper()] for k in env_raw}
        for key in backup:
            del os.environ[key]
        env_parsed = Settings.model_validate(parsed)
        data.update(env_parsed.model_dump())

    result = Settings(**data)
    if env_raw:
        os.environ.update(backup)
    return result
