import base64
import json
import yaml
from massconfigmerger import aggregator_tool
from massconfigmerger.config import Settings


def test_output_files_utf8(tmp_path):
    link = "vmess://uuid@host:443?aid=0&type=auto&security=tls#名"
    aggregator_tool.output_files([link], tmp_path, Settings())

    raw = tmp_path / "vpn_subscription_raw.txt"
    b64 = tmp_path / "vpn_subscription_base64.txt"
    singbox = tmp_path / "vpn_singbox.json"
    clash = tmp_path / "clash.yaml"

    assert raw.read_text(encoding="utf-8") == link
    assert base64.b64decode(b64.read_text(encoding="utf-8")).decode("utf-8") == link
    assert json.loads(singbox.read_text(encoding="utf-8"))
    assert yaml.safe_load(clash.read_text(encoding="utf-8"))
