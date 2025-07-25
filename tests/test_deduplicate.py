import base64
import json
import sys

from massconfigmerger import aggregator_tool
from massconfigmerger.config import Settings


def test_case_insensitive_deduplication():
    data = {"v": "2"}
    b64 = base64.b64encode(json.dumps(data).encode()).decode().strip("=")
    lower = f"vmess://{b64}"
    upper = f"Vmess://{b64}"
    cfg = Settings(
        telegram_api_id=1,
        telegram_api_hash="h",
        telegram_bot_token="t",
        allowed_user_ids=[1],
        protocols=["vmess"],
    )
    result = aggregator_tool.deduplicate_and_filter({lower, upper}, cfg)
    assert len(result) == 1
    assert result[0] in {lower, upper}


def test_exclude_patterns_ignore_case():
    link = "trojan://pw@foo.com:443"
    cfg = Settings(
        telegram_api_id=1,
        telegram_api_hash="h",
        telegram_bot_token="t",
        allowed_user_ids=[1],
        protocols=["trojan"],
        exclude_patterns=["FOO"],
    )
    result = aggregator_tool.deduplicate_and_filter({link}, cfg)
    assert result == []


def test_include_patterns():
    link = "trojan://pw@foo.com:443"
    other = "vmess://a"
    cfg = Settings(
        telegram_api_id=1,
        telegram_api_hash="h",
        telegram_bot_token="t",
        allowed_user_ids=[1],
        protocols=[],
        include_patterns=["foo"],
    )
    result = aggregator_tool.deduplicate_and_filter({link, other}, cfg)
    assert result == [link]


def test_empty_protocol_list_accepts_all():
    data = {"v": "2"}
    b64 = base64.b64encode(json.dumps(data).encode()).decode().strip("=")
    vmess = f"vmess://{b64}"
    trojan = "trojan://pw@foo.com:443"
    cfg = Settings(
        telegram_api_id=1,
        telegram_api_hash="h",
        telegram_bot_token="t",
        allowed_user_ids=[1],
        protocols=[],
    )
    result = aggregator_tool.deduplicate_and_filter({vmess, trojan}, cfg)
    assert set(result) == {vmess, trojan}


def test_protocol_filter_mixed_case_from_cfg():
    data = {"v": "2"}
    b64 = base64.b64encode(json.dumps(data).encode()).decode().strip("=")
    vmess = f"vmess://{b64}"
    trojan = "trojan://pw@foo.com:443"
    cfg = Settings(
        telegram_api_id=1,
        telegram_api_hash="h",
        telegram_bot_token="t",
        allowed_user_ids=[1],
        protocols=["TroJAN"],
    )
    result = aggregator_tool.deduplicate_and_filter({vmess, trojan}, cfg)
    assert result == [trojan]


def test_protocol_filter_mixed_case_argument():
    data = {"v": "2"}
    b64 = base64.b64encode(json.dumps(data).encode()).decode().strip("=")
    vmess = f"vmess://{b64}"
    trojan = "trojan://pw@foo.com:443"
    cfg = Settings(
        telegram_api_id=1,
        telegram_api_hash="h",
        telegram_bot_token="t",
        allowed_user_ids=[1],
        protocols=[],
    )
    result = aggregator_tool.deduplicate_and_filter({vmess, trojan}, cfg, ["VMeSS"])
    assert result == [vmess]


def test_semantic_deduplication_vmess():
    """Links representing the same VMess config should deduplicate."""
    data = {"v": "2", "add": "host", "port": "80", "id": "uuid"}
    json1 = json.dumps(data)
    b64_1 = base64.b64encode(json1.encode()).decode().strip("=")
    link1 = f"vmess://{b64_1}"

    json2 = json.dumps({"id": "uuid", "port": "80", "add": "host", "v": "2"})
    b64_2 = base64.b64encode(json2.encode()).decode().strip("=")
    link2 = f"VMESS://{b64_2}"

    cfg = Settings(
        telegram_api_id=1,
        telegram_api_hash="h",
        telegram_bot_token="t",
        allowed_user_ids=[1],
        protocols=["vmess"],
    )
    result = aggregator_tool.deduplicate_and_filter({link1, link2}, cfg)
    assert len(result) == 1
    assert result[0] in {link1, link2}
