import base64
import json
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse

from .models import Proxy


def _parse_vmess(config: str) -> Proxy | None:
    try:
        data = config[len("vmess://"):]
        decoded = base64.b64decode(data).decode("utf-8")
        vmess_data = json.loads(decoded)
        return Proxy(
            config=config,
            protocol="vmess",
            address=vmess_data.get("add", ""),
            port=int(vmess_data.get("port", 443)),
            uuid=vmess_data.get("id", ""),
            remarks=vmess_data.get("ps", ""),
            details=vmess_data,
        )
    except (json.JSONDecodeError, base64.binascii.Error, KeyError):
        return None


def _parse_vless(config: str) -> Proxy | None:
    try:
        parsed = urlparse(config)
        if not parsed.hostname:
            return None
        query = parse_qs(parsed.query)
        return Proxy(
            config=config,
            protocol="vless",
            address=parsed.hostname,
            port=parsed.port or 443,
            uuid=parsed.username or "",
            remarks=unquote(parsed.fragment or ""),
            details={k: v[0] for k, v in query.items()},
        )
    except (ValueError, IndexError):
        return None


def _parse_ss(config: str) -> Proxy | None:
    try:
        if "@" not in config:
            return None
        encoded_part, host_part = config.replace("ss://", "").split("@", 1)
        decoded_user_info = base64.b64decode(encoded_part).decode("utf-8")
        method, password = decoded_user_info.split(":", 1)
        host, port_remark = host_part.split(":", 1)
        port, remark = (port_remark.split("#", 1)
                        if "#" in port_remark else (port_remark, ""))
        return Proxy(
            config=config,
            protocol="shadowsocks",
            address=host,
            port=int(port),
            remarks=unquote(remark or ""),
            details={
                "method": method,
                "password": password
            },
        )
    except (ValueError, IndexError, base64.binascii.Error):
        return None


def _parse_trojan(config: str) -> Proxy | None:
    try:
        parsed = urlparse(config)
        if not parsed.hostname:
            return None
        return Proxy(
            config=config,
            protocol="trojan",
            address=parsed.hostname,
            port=parsed.port or 443,
            uuid=parsed.username or "",
            remarks=unquote(parsed.fragment or ""),
            details=parse_qs(parsed.query),
        )
    except (ValueError, IndexError):
        return None


def _parse_hysteria(config: str) -> Proxy | None:
    try:
        parsed = urlparse(config)
        if not parsed.hostname:
            return None
        return Proxy(
            config=config,
            protocol="hysteria",
            address=parsed.hostname,
            port=parsed.port or 443,
            uuid=parsed.username or "",
            remarks=unquote(parsed.fragment or ""),
            details=parse_qs(parsed.query),
        )
    except (ValueError, IndexError):
        return None


def _parse_hysteria2(config: str) -> Proxy | None:
    try:
        parsed = urlparse(config)
        if not parsed.hostname:
            return None
        return Proxy(
            config=config,
            protocol="hysteria2",
            address=parsed.hostname,
            port=parsed.port or 443,
            uuid=parsed.username or "",
            remarks=unquote(parsed.fragment or ""),
            details=parse_qs(parsed.query),
        )
    except (ValueError, IndexError):
        return None


def _parse_tuic(config: str) -> Proxy | None:
    try:
        parsed = urlparse(config)
        if not parsed.hostname:
            return None
        return Proxy(
            config=config,
            protocol="tuic",
            address=parsed.hostname,
            port=parsed.port or 443,
            uuid=parsed.username or "",
            remarks=unquote(parsed.fragment or ""),
            details=parse_qs(parsed.query),
        )
    except (ValueError, IndexError):
        return None


def _parse_wireguard(config: str) -> Proxy | None:
    try:
        parsed = urlparse(config)
        if not parsed.hostname:
            return None
        return Proxy(
            config=config,
            protocol="wireguard",
            address=parsed.hostname,
            port=parsed.port or 51820,
            uuid="",
            remarks=unquote(parsed.fragment or ""),
            details=parse_qs(parsed.query),
        )
    except (ValueError, IndexError):
        return None


def _parse_naive(config: str) -> Proxy | None:
    try:
        parsed = urlparse(config.replace("naive+", ""))
        if not parsed.hostname:
            return None
        return Proxy(
            config=config,
            protocol="naive",
            address=parsed.hostname,
            port=parsed.port or 443,
            uuid=parsed.username or "",
            details={"password": parsed.password or ""},
            remarks=unquote(parsed.fragment or ""),
        )
    except (ValueError, IndexError):
        return None


def _parse_generic(config: str) -> Proxy | None:
    try:
        parsed = urlparse(config)
        if not parsed.hostname:
            return None
        return Proxy(
            config=config,
            protocol=parsed.scheme,
            address=parsed.hostname,
            port=parsed.port or 80,
            uuid=parsed.username or "",
            details={"password": parsed.password or ""},
            remarks=unquote(parsed.fragment or ""),
        )
    except (ValueError, IndexError):
        return None