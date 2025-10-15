from __future__ import annotations

import requests


def test_config(config: str, timeout: int) -> tuple[str, bool]:
    """
    Tests a single configuration by making a request to a test URL.
    This is a placeholder and should be replaced with actual test logic.
    """
    try:
        # In a real scenario, you would configure the request to use the proxy.
        # For this placeholder, we'll just make a simple request.
        response = requests.get("http://www.google.com/generate_204", timeout=timeout)
        return config, response.status_code == 204
    except requests.RequestException:
        return config, False


def test_configs(configs: list[str]) -> list[tuple[str, bool]]:
    """
    Tests a list of configurations.
    """
    results = []
    for config in configs:
        # In a real implementation, you might use a thread pool to run these in parallel.
        results.append(test_config(config, timeout=5))
    return results
