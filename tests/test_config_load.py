import json
import os
import sys
from pathlib import Path
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from aggregator_tool import Config


def test_load_defaults(tmp_path):
    cfg = {
        "telegram_api_id": 1,
        "telegram_api_hash": "hash",
        "telegram_bot_token": "token",
        "allowed_user_ids": [1]
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg))
    loaded = Config.load(p)
    assert loaded.output_dir == "output"
    assert loaded.log_dir == "logs"
    assert loaded.protocols == []
    assert loaded.exclude_patterns == []
    assert loaded.max_concurrent == 20


def test_load_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ invalid }")
    with pytest.raises(ValueError):
        Config.load(p)
