import asyncio
import logging
from datetime import datetime

from .parsers import (_parse_generic, _parse_hysteria, _parse_hysteria2,
                    _parse_naive, _parse_ss, _parse_trojan, _parse_tuic,
                    _parse_vless, _parse_vmess, _parse_wireguard)

from .models import Proxy

logger = logging.getLogger(__name__)


def parse_config(config_string: str) -> Proxy | None:
    if not config_string or not isinstance(config_string, str):
        return None

    config_string = config_string.strip()
    if not config_string or config_string.startswith("#"):
        return None

    try:
        if config_string.startswith("vmess://"):
            return _parse_vmess(config_string)
        if config_string.startswith("vless://"):
            return _parse_vless(config_string)
        if config_string.startswith("ss://"):
            return _parse_ss(config_string)
        if config_string.startswith("trojan://"):
            return _parse_trojan(config_string)
        if config_string.startswith("hysteria://"):
            return _parse_hysteria(config_string)
        if config_string.startswith("hy2://") or config_string.startswith(
                "hysteria2://"):
            return _parse_hysteria2(config_string)
        if config_string.startswith("tuic://"):
            return _parse_tuic(config_string)
        if config_string.startswith("wg://") or config_string.startswith(
                "wireguard://"):
            return _parse_wireguard(config_string)
        if config_string.startswith("naive+https://"):
            return _parse_naive(config_string)
        if any(
                config_string.startswith(f"{p}://")
                for p in
            ["ssh", "http", "https", "socks", "socks4", "socks5"]):
            return _parse_generic(config_string)

        logger.debug(f"Unknown protocol in config: {config_string[:50]}...")
        return None

    except Exception as e:
        logger.debug(f"Error parsing config: {e}")
        return None


def parse_config_batch(config_strings: list[str]) -> list[Proxy]:
    parsed = []
    for config_string in config_strings:
        proxy = parse_config(config_string)
        if proxy is not None:
            parsed.append(proxy)
    return parsed


async def geolocate_proxy(proxy: Proxy, geoip_reader=None) -> Proxy:
    if geoip_reader is None:
        proxy.country = "Unknown"
        proxy.country_code = "XX"
        return proxy
    try:
        response = geoip_reader.city(proxy.address)
        proxy.country = response.country.name or "Unknown"
        proxy.country_code = response.country.iso_code or "XX"
        proxy.city = response.city.name or "Unknown"
        proxy.asn = f"AS{response.autonomous_system.autonomous_system_number}"
    except Exception:
        proxy.country = "Unknown"
        proxy.country_code = "XX"
    return proxy

