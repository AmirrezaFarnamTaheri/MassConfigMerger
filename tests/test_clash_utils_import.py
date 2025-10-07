from configstream.clash_utils import config_to_clash_proxy


def test_config_to_clash_proxy_import():
    proxy = config_to_clash_proxy("naive://user:pass@host:443", 0)
    assert proxy["type"] == "http"
    assert proxy["tls"] is True
