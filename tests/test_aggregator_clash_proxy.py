import os
import sys
import yaml

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import aggregator_tool
from massconfigmerger.config import Settings


def test_aggregator_clash_proxy(tmp_path):
    cfg = Settings(output_dir=str(tmp_path), write_clash=True)
    configs = [
        "reality://uuid@host:443?flow=xtls-rprx-vision",
        "naive://user:pass@host:443",
    ]
    aggregator_tool.output_files(configs, tmp_path, cfg)
    data = yaml.safe_load((tmp_path / "clash.yaml").read_text())
    reality = next(p for p in data["proxies"] if p.get("flow"))
    assert reality["type"] == "vless"
    assert reality["tls"] is True
    naive = next(p for p in data["proxies"] if p["type"] == "http")
    assert naive["tls"] is True
