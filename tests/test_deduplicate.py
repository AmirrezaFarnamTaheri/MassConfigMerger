import base64
import json
import os

from massconfigmerger import aggregator_tool


def test_case_insensitive_deduplication():
    data = {"v": "2"}
    b64 = base64.b64encode(json.dumps(data).encode()).decode().strip("=")
    lower = f"vmess://{b64}"
    upper = f"Vmess://{b64}"
    cfg = aggregator_tool.Config(
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
    cfg = aggregator_tool.Config(
        telegram_api_id=1,
        telegram_api_hash="h",
        telegram_bot_token="t",
        allowed_user_ids=[1],
        protocols=["trojan"],
        exclude_patterns=["FOO"],
    )
    result = aggregator_tool.deduplicate_and_filter({link}, cfg)
    assert result == []


def test_empty_protocol_list_accepts_all():
    data = {"v": "2"}
    b64 = base64.b64encode(json.dumps(data).encode()).decode().strip("=")
    vmess = f"vmess://{b64}"
    trojan = "trojan://pw@foo.com:443"
    cfg = aggregator_tool.Config(
        telegram_api_id=1,
        telegram_api_hash="h",
        telegram_bot_token="t",
        allowed_user_ids=[1],
        protocols=[],
    )
    result = aggregator_tool.deduplicate_and_filter({vmess, trojan}, cfg)
    assert set(result) == {vmess, trojan}

