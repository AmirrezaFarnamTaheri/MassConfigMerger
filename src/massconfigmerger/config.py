import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml
from pydantic import BaseSettings, Field, Extra, ValidationError


class Settings(BaseSettings):
    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    allowed_user_ids: List[int] = Field(default_factory=list)
    protocols: List[str] = Field(default_factory=list)
    exclude_patterns: List[str] = Field(default_factory=list)
    output_dir: str = "output"
    log_dir: str = "logs"
    request_timeout: int = 10
    max_concurrent: int = 20
    write_base64: bool = True
    write_singbox: bool = True
    write_clash: bool = True

    headers: Dict[str, str] = Field(
        default_factory=lambda: {
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
    )
    connect_timeout: float = 3.0
    max_retries: int = 3
    concurrent_limit: int = 50
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
    test_timeout: float = 5.0
    batch_size: int = 1000
    threshold: int = 0
    top_n: int = 0
    tls_fragment: Optional[str] = None
    include_protocols: Optional[Set[str]] = Field(
        default_factory=lambda: {
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
    )
    exclude_protocols: Optional[Set[str]] = Field(default_factory=lambda: {"OTHER"})
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

    class Config:
        env_prefix = ""
        extra = Extra.forbid


def load_settings(path: Path | str = Path("config.yaml"), defaults: dict | None = None) -> Settings:
    path = Path(path)
    data = {}
    if path.exists():
        with path.open() as f:
            raw = yaml.safe_load(f) or {}
        if not isinstance(raw, dict):
            raise ValueError(f"{path} must contain a YAML mapping")
        data.update(raw)
    else:
        raise ValueError(f"Config file not found: {path}")
    if defaults:
        for key, value in defaults.items():
            data.setdefault(key, value)
    env_overrides: dict[str, object] = {}
    removed: list[tuple[str, str]] = []
    if "TELEGRAM_API_ID" in os.environ:
        removed.append(("TELEGRAM_API_ID", os.environ.pop("TELEGRAM_API_ID")))
        env_overrides["telegram_api_id"] = int(removed[-1][1])
    for key in ("TELEGRAM_API_HASH", "TELEGRAM_BOT_TOKEN"):
        if key in os.environ:
            removed.append((key, os.environ.pop(key)))
            env_overrides[key.lower()] = removed[-1][1]
    if "ALLOWED_USER_IDS" in os.environ:
        raw = os.environ.pop("ALLOWED_USER_IDS")
        removed.append(("ALLOWED_USER_IDS", raw))
        ids = [int(i) for i in re.split(r"[ ,]+", raw.strip()) if i]
        env_overrides["allowed_user_ids"] = ids
    env_names = {name.upper() for name in os.environ}
    data = {k: v for k, v in data.items() if k.upper() not in env_names}
    data.update(env_overrides)
    try:
        return Settings(**data)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
    finally:
        for k, v in removed:
            os.environ[k] = v


try:
    settings = load_settings()
except ValueError:
    settings = Settings()

