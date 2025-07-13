from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml
from pydantic import BaseModel

# Root of the repository
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = _REPO_ROOT / "config.yaml"

DEFAULT_HEADERS = {
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

DEFAULT_PREFIXES: Tuple[str, ...] = (
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


class Settings(BaseModel):
    """Unified configuration model."""

    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    allowed_user_ids: List[int] = []

    protocols: List[str] = []
    exclude_patterns: List[str] = []
    output_dir: str = "output"
    log_dir: str = "logs"
    request_timeout: int = 10
    max_concurrent: int = 20
    write_base64: bool = True
    write_singbox: bool = True
    write_clash: bool = True

    # vpn_merger settings
    headers: Dict[str, str] = DEFAULT_HEADERS
    connect_timeout: float = 3.0
    max_retries: int = 3
    concurrent_limit: int = 50
    max_configs_per_source: int = 75000
    valid_prefixes: Tuple[str, ...] = DEFAULT_PREFIXES
    enable_url_testing: bool = True
    enable_sorting: bool = True
    test_timeout: float = 5.0
    batch_size: int = 1000
    threshold: int = 0
    top_n: int = 0
    tls_fragment: Optional[str] = None
    include_protocols: Optional[Set[str]] = {
        "PROXY",
        "SHADOWSOCKS",
        "SHADOWSOCKSR",
        "TROJAN",
        "CLASH",
        "V2RAY",
        "REALITY",
        "VMESS",
        "XRAY",
        "WIREGUARD",
        "ECH",
        "VLESS",
        "HYSTERIA",
        "TUIC",
        "SING-BOX",
        "SINGBOX",
        "SHADOWTLS",
        "CLASHMETA",
        "HYSTERIA2",
    }
    exclude_protocols: Optional[Set[str]] = {"OTHER"}
    resume_file: Optional[str] = None
    max_ping_ms: Optional[int] = 1000
    log_file: Optional[str] = None
    cumulative_batches: bool = False
    strict_batch: bool = True
    shuffle_sources: bool = False
    write_csv: bool = True
    write_clash_proxies: bool = True
    mux_concurrency: int = 8
    smux_streams: int = 4
    geoip_db: Optional[str] = None
    include_countries: Optional[Set[str]] = None
    exclude_countries: Optional[Set[str]] = None




def load_settings(path: Path | None = None) -> Settings:
    """Load configuration from ``config.yaml`` with environment overrides."""
    if path is None:
        path = DEFAULT_CONFIG_PATH
    data = {}
    if path.exists():
        try:
            loaded = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ValueError(f"{path} must contain a mapping")
        data.update(loaded)
    else:
        if path != DEFAULT_CONFIG_PATH:
            raise ValueError(f"Config file not found: {path}")
    env_data: dict[str, str] = {k.lower(): v for k, v in os.environ.items() if k.lower() in Settings.model_fields}
    if "allowed_user_ids" in env_data:
        env_data["allowed_user_ids"] = [int(i) for i in re.split(r"[ ,]+", env_data["allowed_user_ids"].strip()) if i]
    data.update(env_data)
    return Settings(**data)


# Global shared configuration instance
settings = load_settings()

__all__ = ["Settings", "load_settings", "settings"]
