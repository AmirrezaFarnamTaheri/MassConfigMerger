from __future__ import annotations

import base64
import json
from urllib.parse import parse_qs, unquote, urlparse

from .core import Proxy


def parse_config(config: str) -> Proxy | None:
    """Parse a raw proxy configuration string."""
    if config.startswith("vmess://"):
        return _parse_vmess(config)
    elif config.startswith("vless://"):
        return _parse_vless(config)
    elif config.startswith("ss://"):
        return _parse_ss(config)
    elif config.startswith("trojan://"):
        return _parse_trojan(config)
    elif config.startswith("hy2://") or config.startswith("hysteria2://"):
        return _parse_hysteria2(config)
    elif config.startswith("hysteria://"):
        return _parse_hysteria(config)
    elif config.startswith("tuic://"):
        return _parse_tuic(config)
    elif config.startswith("wg://") or config.startswith("wireguard://"):
        return _parse_wireguard(config)
    elif any(
            config.startswith(f"{p}://")
            for p in ["ssh", "http", "https", "socks", "socks4", "socks5"]):
        return _parse_generic(config)
    elif config.startswith("naive+https://"):
        return _parse_naive(config)
    return None


def _parse_naive(config: str) -> Proxy | None:
    """Parse naive+https:// URI."""
    try:
        parsed = urlparse(config.replace("naive+", ""))
        query = parse_qs(parsed.query)

        details = {k: v[0] for k, v in query.items()}
        if parsed.password:
            details["password"] = parsed.password

        return Proxy(
            config=config,
            protocol="naive",
            remarks=unquote(parsed.fragment or ""),
            address=parsed.hostname or "",
            port=parsed.port or 443,
            uuid=parsed.username or "",
            _details=details,
        )
    except Exception:
        return None


def _parse_wireguard(config: str) -> Proxy | None:
    """Parse wireguard:// URI."""
    try:
        parsed = urlparse(config)
        query = parse_qs(parsed.query)

        return Proxy(
            config=config,
            protocol="wireguard",
            remarks=unquote(parsed.fragment or ""),
            address=parsed.hostname or "",
            port=parsed.port or 51820,
            _details={
                k: v[0]
                for k, v in query.items()
            },
        )
    except Exception:
        return None


def _parse_hysteria2(config: str) -> Proxy | None:
    """Parse hy2:// or hysteria2:// URI."""
    try:
        parsed = urlparse(config)
        query = parse_qs(parsed.query)

        return Proxy(
            config=config,
            protocol="hysteria2",
            remarks=unquote(parsed.fragment or ""),
            address=parsed.hostname or "",
            port=parsed.port or 443,
            uuid=parsed.username or "",
            _details={
                k: v[0]
                for k, v in query.items()
            },
        )
    except Exception:
        return None


def _parse_hysteria(config: str) -> Proxy | None:
    """Parse hysteria:// URI."""
    try:
        parsed = urlparse(config)
        query = parse_qs(parsed.query)

        return Proxy(
            config=config,
            protocol="hysteria",
            remarks=unquote(parsed.fragment or ""),
            address=parsed.hostname or "",
            port=parsed.port or 443,
            uuid=parsed.username or "",
            _details={
                k: v[0]
                for k, v in query.items()
            },
        )
    except Exception:
        return None


def _parse_tuic(config: str) -> Proxy | None:
    """Parse tuic:// URI."""
    try:
        parsed = urlparse(config)
        query = parse_qs(parsed.query)

        # TUIC format: tuic://uuid:password@server:port
        uuid_pass = parsed.username
        uuid = uuid_pass.split(
            ":")[0] if uuid_pass and ":" in uuid_pass else uuid_pass

        return Proxy(
            config=config,
            protocol="tuic",
            remarks=unquote(parsed.fragment or ""),
            address=parsed.hostname or "",
            port=parsed.port or 443,
            uuid=uuid or "",
            _details={
                k: v[0]
                for k, v in query.items()
            },
        )
    except Exception:
        return None


def _parse_generic(config: str) -> Proxy | None:
    """Parse generic URI format."""
    try:
        parsed = urlparse(config)
        query = parse_qs(parsed.query)

        details = {k: v[0] for k, v in query.items()}
        if parsed.password:
            details["password"] = parsed.password

        return Proxy(
            config=config,
            protocol=parsed.scheme,
            remarks=unquote(parsed.fragment or ""),
            address=parsed.hostname or "",
            port=parsed.port or 0,
            uuid=parsed.username or "",
            _details=details,
        )
    except Exception:
        return None


def _parse_trojan(config: str) -> Proxy | None:
    """Parse trojan:// URI."""
    try:
        parsed = urlparse(config)
        query = parse_qs(parsed.query)

        return Proxy(
            config=config,
            protocol="trojan",
            remarks=unquote(parsed.fragment or ""),
            address=parsed.hostname or "",
            port=parsed.port or 443,
            uuid=parsed.username or "",
            _details={
                k: v[0]
                for k, v in query.items()
            },
        )
    except Exception:
        return None


def _parse_ss(config: str) -> Proxy | None:
    """Parse ss:// URI."""
    try:
        parsed = urlparse(config)

        encoded = parsed.username or ""
        padded = encoded + "=" * (-len(encoded) % 4)
        decoded = base64.b64decode(padded).decode("utf-8")

        if ":" not in decoded:
            return None

        method, password = decoded.split(":", 1)

        return Proxy(
            config=config,
            protocol="shadowsocks",
            remarks=unquote(parsed.fragment or ""),
            address=parsed.hostname or "",
            port=parsed.port or 8388,
            _details={
                "method": method,
                "password": password
            },
        )
    except Exception:
        return None


def _parse_vless(config: str) -> Proxy | None:
    """Parse vless:// URI."""
    try:
        parsed = urlparse(config)
        query = parse_qs(parsed.query)

        return Proxy(
            config=config,
            protocol="vless",
            remarks=unquote(parsed.fragment or ""),
            address=parsed.hostname or "",
            port=parsed.port or 443,
            uuid=parsed.username or "",
            _details={
                k: v[0]
                for k, v in query.items()
            },
        )
    except Exception:
        return None


def _parse_vmess(config: str) -> Proxy | None:
    """Parse vmess:// URI."""
    try:
        encoded = config[len("vmess://"):]
        padded = encoded + "=" * (-len(encoded) % 4)
        decoded = base64.b64decode(padded).decode("utf-8")
        details = json.loads(decoded)

        return Proxy(
            config=config,
            protocol="vmess",
            remarks=details.get("ps", ""),
            address=details.get("add", ""),
            port=int(details.get("port", 0)),
            uuid=details.get("id", ""),
            security=details.get("scy", "auto"),
            _details=details,
        )
    except Exception:
        return None
