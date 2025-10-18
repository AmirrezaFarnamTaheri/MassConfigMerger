import base64
import json
from typing import List

import yaml

from .core import Proxy


def generate_base64_subscription(proxies: list[Proxy]) -> str:
    working_proxies = [p for p in proxies if p.is_working]
    if not working_proxies:
        return ""
    configs = [p.config for p in working_proxies]
    return base64.b64encode("\n".join(configs).encode()).decode()


def generate_clash_config(proxies: list[Proxy]) -> str:
    working_proxies = [p for p in proxies if p.is_working]
    clash_proxies = []
    for p in working_proxies:
        proxy_data = {
            "name": p.remarks or f"{p.protocol}-{p.address}",
            "type": p.protocol,
            "server": p.address,
            "port": p.port,
            "uuid": p.uuid,
        }
        if p.details:
            proxy_data.update(p.details)
        clash_proxies.append(proxy_data)
    return yaml.dump({
        "proxies": clash_proxies,
        "proxy-groups": [{
            "name": "🚀 ConfigStream",
            "type": "select",
            "proxies": [p["name"] for p in clash_proxies],
        }],
    })


def generate_singbox_config(proxies: list[Proxy]) -> str:
    # Dummy implementation
    return json.dumps({"outbounds": []})