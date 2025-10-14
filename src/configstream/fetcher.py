from __future__ import annotations

import requests


def fetch_all(sources: list[str]) -> list[str]:
    """
    Fetches all configurations from the given sources.
    """
    configs = []
    for source in sources:
        try:
            response = requests.get(source, timeout=10)
            response.raise_for_status()
            configs.extend(response.text.splitlines())
        except requests.RequestException as e:
            print(f"Error fetching {source}: {e}")
    return configs