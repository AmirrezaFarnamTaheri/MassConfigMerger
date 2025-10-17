from configstream.config import ProxyConfig


def test_proxy_config_load_defaults():
    """
    Test that the default proxy configurations are loaded correctly.
    """
    config = ProxyConfig()
    assert config.TEST_TIMEOUT == 10
    assert config.BATCH_SIZE == 50
    assert config.RATE_LIMIT_REQUESTS == 100
    assert "vmess" in config.PROTOCOL_COLORS
    assert "primary" in config.TEST_URLS
    assert "blocked_countries" in config.SECURITY
