"""Utility helpers for protocol detection and parsing."""

from __future__ import annotations

import base64
import binascii
import json
import logging
import re
from urllib.parse import urlparse
from typing import Set

from .config import Settings

from .constants import PROTOCOL_RE, BASE64_RE, MAX_DECODE_SIZE

_warning_printed = False


def print_public_source_warning() -> None:
    """Print a usage warning once per execution."""
    global _warning_printed
    if not _warning_printed:
        print(
            "WARNING: Collected VPN nodes come from public sources. "
            "Use at your own risk and comply with local laws."
        )
        _warning_printed = True


def is_valid_config(link: str) -> bool:
    """Simple validation for known protocols."""
    if "warp://" in link:
        return False

    scheme, _, rest = link.partition("://")
    scheme = scheme.lower()
    rest = re.split(r"[?#]", rest, 1)[0]

    if scheme == "vmess":
        padded = rest + "=" * (-len(rest) % 4)
        try:
            json.loads(base64.b64decode(padded, validate=True).decode())
            return True
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            logging.warning("Invalid vmess config: %s", exc)
            return False

    if scheme == "ssr":
        encoded = rest
        padded = encoded + "=" * (-len(encoded) % 4)
        try:
            decoded = base64.urlsafe_b64decode(padded).decode()
        except (binascii.Error, UnicodeDecodeError) as exc:
            logging.warning("Invalid ssr config encoding: %s", exc)
            return False
        host_part = decoded.split("/", 1)[0]
        if ":" not in host_part:
            return False
        host, port = host_part.split(":", 1)
        return bool(host and port)

    host_required = {
        "naive",
        "hy2",
        "vless",
        "trojan",
        "reality",
        "hysteria",
        "hysteria2",
        "tuic",
        "ss",
    }
    if scheme in host_required:
        if "@" not in rest:
            return False
        host = rest.split("@", 1)[1].split("/", 1)[0]
        return ":" in host

    simple_host_port = {
        "http",
        "https",
        "grpc",
        "ws",
        "wss",
        "socks",
        "socks4",
        "socks5",
        "tcp",
        "kcp",
        "quic",
        "h2",
    }
    if scheme in simple_host_port:
        parsed = urlparse(link)
        return bool(parsed.hostname and parsed.port)
    if scheme == "wireguard":
        return bool(rest)

    return bool(rest)


def parse_configs_from_text(text: str) -> Set[str]:
    """Extract all config links from a text block."""
    configs: Set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        matches = PROTOCOL_RE.findall(line)
        if matches:
            configs.update(matches)
            continue
        if BASE64_RE.match(line):
            if len(line) > MAX_DECODE_SIZE:
                logging.debug(
                    "Skipping oversized base64 line (%d > %d)",
                    len(line),
                    MAX_DECODE_SIZE,
                )
                continue
            try:
                padded = line + "=" * (-len(line) % 4)
                decoded = base64.urlsafe_b64decode(padded).decode()
                configs.update(PROTOCOL_RE.findall(decoded))
            except (binascii.Error, UnicodeDecodeError) as exc:
                logging.debug("Failed to decode base64 line: %s", exc)
                continue
    return configs


def choose_proxy(cfg: Settings) -> str | None:
    """Return SOCKS proxy if defined, otherwise HTTP proxy."""
    return cfg.SOCKS_PROXY or cfg.HTTP_PROXY
