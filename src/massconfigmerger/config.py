from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Application configuration loaded from YAML with env overrides."""

    # Telegram / aggregator settings
    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    allowed_user_ids: List[int] = []

    protocols: List[str] = []
    exclude_patterns: List[str] = []
    output_dir: str = "output"
    log_dir: str = "logs"
    request_timeout: int = 10
    concurrent_limit: int = 20
    retry_attempts: int = 3
    retry_base_delay: float = 1.0
    write_base64: bool = True
    write_singbox: bool = True
    write_clash: bool = True

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

    model_config = SettingsConfigDict(env_prefix="")

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        return init_settings,

    @classmethod
    def load(cls, path: Path, defaults: dict | None = None) -> "AppConfig":
        """Load configuration from a YAML file applying defaults and env vars."""
        try:
            data = yaml.safe_load(path.read_text()) or {}
        except FileNotFoundError as exc:
            raise ValueError(f"Config file not found: {path}") from exc
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in {path}: {exc}") from exc

        if defaults:
            for k, v in defaults.items():
                data.setdefault(k, v)

        env = os.getenv
        env_map = {
            "telegram_api_id": env("TELEGRAM_API_ID"),
            "telegram_api_hash": env("TELEGRAM_API_HASH"),
            "telegram_bot_token": env("TELEGRAM_BOT_TOKEN"),
            "allowed_user_ids": env("ALLOWED_USER_IDS"),
        }
        if env_map["telegram_api_id"] is not None:
            try:
                data["telegram_api_id"] = int(env_map["telegram_api_id"])
            except ValueError as exc:
                raise ValueError("TELEGRAM_API_ID must be an integer") from exc
        for key in ("telegram_api_hash", "telegram_bot_token"):
            if env_map[key] is not None:
                data[key] = env_map[key]
        if env_map["allowed_user_ids"] is not None:
            try:
                ids = [
                    int(i)
                    for i in re.split(r"[ ,]+", env_map["allowed_user_ids"].strip())
                    if i
                ]
            except ValueError as exc:
                raise ValueError(
                    "ALLOWED_USER_IDS must be a comma separated list of integers"
                ) from exc
            data["allowed_user_ids"] = ids

        if "allowed_user_ids" in data:
            try:
                data["allowed_user_ids"] = [int(i) for i in data["allowed_user_ids"]]
            except Exception as exc:
                raise ValueError("allowed_user_ids must be a list of integers") from exc

        return cls(**data)
