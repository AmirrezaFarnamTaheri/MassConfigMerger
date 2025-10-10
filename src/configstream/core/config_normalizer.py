# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import logging
import re
from typing import Optional, Tuple
from urllib.parse import parse_qsl, parse_qs, urlencode, urlparse, urlunparse

from ..config import Settings
from ..constants import MAX_DECODE_SIZE
from .parsers.common import BaseParser
from .parsers.hysteria import HysteriaParser
from .parsers.shadowsocks import ShadowsocksParser
from .parsers.trojan import TrojanParser
from .parsers.vmess import VmessParser


def extract_host_port(
    config: str, max_decode_size: int = MAX_DECODE_SIZE
) -> Tuple[Optional[str], Optional[int]]:
    """Extract host and port from configuration for testing."""
    try:
        if config.startswith(("vmess://", "vless://")):
            try:
                json_part = config.split("://", 1)[1]
                padded = json_part + "=" * (-len(json_part) % 4)
                decoded_bytes = base64.b64decode(padded)
                if len(decoded_bytes) > max_decode_size:
                    return None, None
                decoded = decoded_bytes.decode("utf-8", "ignore")
                data = json.loads(decoded)
                host = data.get("add") or data.get("host")
                port = data.get("port")
                return host, int(port) if port else None
            except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
                # Fallback to URI-style parsing (common for VLESS)
                p = urlparse(config)
                if p.hostname and p.port:
                    return p.hostname, p.port
                logging.debug(
                    "extract_host_port vmess/vless fallback failed for: %s", config)

        if config.startswith("ssr://"):
            try:
                after = config.split("://", 1)[1].split("#", 1)[0]
                padded = after + "=" * (-len(after) % 4)
                decoded_bytes = base64.urlsafe_b64decode(padded)
                if len(decoded_bytes) > max_decode_size:
                    return None, None
                decoded = decoded_bytes.decode("utf-8")
                host_part = decoded.split("/", 1)[0]
                parts = host_part.split(":")
                if len(parts) < 2:
                    return None, None
                host, port = parts[0], parts[1]
                return host or None, int(port)
            except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
                logging.debug("extract_host_port ssr failed: %s", exc)

        parsed = urlparse(config)
        if parsed.hostname and parsed.port:
            return parsed.hostname, parsed.port

        match = re.search(r"@([^:/?#]+):(\d+)", config)
        if match:
            return match.group(1), int(match.group(2))

    except (ValueError, UnicodeError, binascii.Error) as exc:
        logging.debug("extract_host_port failed: %s", exc)
    return None, None


def _normalize_url(config: str, max_decode_size: int = MAX_DECODE_SIZE) -> str:
    """Return canonical URL with sorted query params and no fragment."""
    parsed = urlparse(config)
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    sorted_query = urlencode(sorted(query_pairs), doseq=True)

    scheme = parsed.scheme.lower()
    if scheme in {"vmess", "vless"}:
        payload = parsed.netloc or parsed.path.lstrip("/")
        if payload:
            try:
                padded = payload + "=" * (-len(payload) % 4)
                decoded_bytes = base64.b64decode(padded)
                if len(decoded_bytes) > max_decode_size:
                    return urlunparse(parsed._replace(query=sorted_query, fragment=""))
                decoded = decoded_bytes.decode("utf-8", "ignore")
                data = json.loads(decoded)
                canonical_json = json.dumps(data, sort_keys=True)
                payload = (
                    base64.b64encode(canonical_json.encode()
                                     ).decode().rstrip("=")
                )
                parsed = parsed._replace(netloc=payload, path="")
            except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
                pass

    return urlunparse(parsed._replace(query=sorted_query, fragment=""))


def get_parser(config: str, idx: int) -> Optional[BaseParser]:
    """Get the appropriate parser for a given configuration URI."""
    scheme = urlparse(config).scheme.lower()
    if scheme in ("vmess", "vless"):
        return VmessParser(config, idx)
    if scheme == "trojan":
        return TrojanParser(config, idx)
    if scheme in ("ss", "shadowsocks"):
        return ShadowsocksParser(config, idx)
    if scheme in ("hysteria", "hy2", "hysteria2"):
        return HysteriaParser(config, idx, scheme)
    return None


def apply_tuning(config: str, settings: Settings) -> str:
    """Apply mux and smux parameters to URI-style configs."""
    try:
        if "//" not in config or config.startswith("vmess://"):
            return config
        parsed = urlparse(config)
        if not parsed.scheme:
            return config
        params = parse_qs(parsed.query)
        if settings.processing.mux_concurrency > 0:
            params["mux"] = [str(settings.processing.mux_concurrency)]
        if settings.processing.smux_streams > 0:
            params["smux"] = [str(settings.processing.smux_streams)]
        new_query = urlencode(params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))
    except ValueError as exc:
        logging.debug("apply_tuning failed: %s", exc)
        return config


def create_semantic_hash(config: str, idx: int) -> str:
    """
    Create a stable, shortened semantic hash for a configuration URL.
    The hash focuses on functional parts (host, port, credentials) and
    is insensitive to non-functional parts like fragments.
    """
    try:
        parsed = urlparse(config)
        if parsed.scheme in {"trojan", "ss", "shadowsocks"}:
            key_parts = (
                parsed.scheme or "",
                parsed.hostname or "",
                str(parsed.port or ""),
                parsed.username or "",
                parsed.password or "",
            )
            semantic_key = ":".join(key_parts)
        else:
            semantic_key = _normalize_url(config)
        digest = hashlib.sha256(semantic_key.encode("utf-8")).hexdigest()
        return digest[:16]
    except Exception as e:
        logging.debug(
            "Semantic hash failed for '%s': %s. Falling back.", config, e)
        fallback_key = f"{config}:{idx}"
        return hashlib.sha256(fallback_key.encode("utf-8")).hexdigest()[:16]
