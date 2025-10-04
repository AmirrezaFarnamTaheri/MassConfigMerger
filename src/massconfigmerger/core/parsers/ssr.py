from __future__ import annotations

import base64
import binascii
import logging
from typing import Any, Dict, Optional
from urllib.parse import parse_qs

from .common import sanitize_str


def parse(config: str, idx: int) -> Optional[Dict[str, Any]]:
    """
    Parse a ShadowsocksR (SSR) configuration link.

    Args:
        config: The SSR configuration link.
        idx: The index of the configuration, used for default naming.

    Returns:
        A dictionary representing the Clash proxy, or None if parsing fails.
    """
    base = config.split("://", 1)[1].split("#", 1)[0]
    name = f"ssr-{idx}"
    try:
        padded = base + "=" * (-len(base) % 4)
        decoded = base64.urlsafe_b64decode(padded).decode()
        main, _, tail = decoded.partition("/")
        parts = main.split(":")
        if len(parts) < 6:
            return None
        server, port_str, proto, method, obfs, pwd_enc = parts[:6]

        try:
            password_decoded = base64.urlsafe_b64decode(pwd_enc + "=" * (-len(pwd_enc) % 4)).decode()
            password = sanitize_str(password_decoded)
        except (binascii.Error, UnicodeDecodeError):
            password = sanitize_str(pwd_enc)

        q = parse_qs(tail[1:]) if tail.startswith("?") else {}
        proxy = {
            "name": name,
            "type": "ssr",
            "server": sanitize_str(server),
            "port": int(port_str),
            "cipher": sanitize_str(method),
            "password": password,
            "protocol": sanitize_str(proto),
            "obfs": sanitize_str(obfs),
        }

        for param, key in [("obfsparam", "obfs-param"), ("protoparam", "protocol-param"), ("remarks", "name"), ("group", "group")]:
            if param in q:
                try:
                    val = base64.urlsafe_b64decode(q[param][0] + "=" * (-len(q[param][0]) % 4)).decode()
                except (binascii.Error, UnicodeDecodeError):
                    val = q[param][0]
                proxy[key] = sanitize_str(val)

        if "udpport" in q:
            try:
                proxy["udpport"] = int(q["udpport"][0])
            except ValueError:
                logging.debug("Could not parse udpport '%s' as integer.", q["udpport"][0])
        if "uot" in q:
            proxy["uot"] = sanitize_str(q["uot"][0])
        return proxy
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        logging.debug("SSR parse failed: %s", exc)
        return None