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


def test_file_not_found(tmp_path):
    missing = tmp_path / "absent.json"
    with pytest.raises(ValueError):
        Config.load(missing)


def test_load_without_credentials(tmp_path):
    """Loading an empty config should succeed with Telegram fields unset."""
    p = tmp_path / "cfg.json"
    p.write_text("{}")
    cfg = Config.load(p)
    assert cfg.telegram_api_id is None
    assert cfg.telegram_api_hash is None
    assert cfg.telegram_bot_token is None
    assert cfg.allowed_user_ids == []


def test_custom_defaults(tmp_path):
    cfg = {
        "telegram_api_id": 1,
        "telegram_api_hash": "hash",
        "telegram_bot_token": "token",
        "allowed_user_ids": [1],
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg))
    loaded = Config.load(p, defaults={"output_dir": "alt"})
    assert loaded.output_dir == "alt"


def test_env_fallback(tmp_path, monkeypatch):
    p = tmp_path / "config.json"
    p.write_text("{}")
    monkeypatch.setenv("TELEGRAM_API_ID", "42")
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("ALLOWED_USER_IDS", "1")
    loaded = Config.load(p)
    assert loaded.telegram_api_id == 42
    assert loaded.telegram_api_hash == "hash"
    assert loaded.telegram_bot_token == "token"
    assert loaded.allowed_user_ids == [1]


def test_env_override(tmp_path, monkeypatch):
    cfg = {
        "telegram_api_id": 1,
        "telegram_api_hash": "hash",
        "telegram_bot_token": "token",
        "allowed_user_ids": [1],
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg))
    monkeypatch.setenv("TELEGRAM_API_ID", "99")
    monkeypatch.setenv("TELEGRAM_API_HASH", "newhash")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "newtoken")
    loaded = Config.load(p)
    assert loaded.telegram_api_id == 99
    assert loaded.telegram_api_hash == "newhash"
    assert loaded.telegram_bot_token == "newtoken"


def test_allowed_ids_env_fallback(tmp_path, monkeypatch):
    cfg = {
        "telegram_api_id": 1,
        "telegram_api_hash": "hash",
        "telegram_bot_token": "token",
    }
    p = tmp_path / "c.json"
    p.write_text(json.dumps(cfg))
    monkeypatch.setenv("ALLOWED_USER_IDS", "5,6")
    loaded = Config.load(p)
    assert loaded.allowed_user_ids == [5, 6]


def test_allowed_ids_env_override(tmp_path, monkeypatch):
    cfg = {
        "telegram_api_id": 1,
        "telegram_api_hash": "hash",
        "telegram_bot_token": "token",
        "allowed_user_ids": [1],
    }
    p = tmp_path / "c.json"
    p.write_text(json.dumps(cfg))
    monkeypatch.setenv("ALLOWED_USER_IDS", "2 3")
    loaded = Config.load(p)
    assert loaded.allowed_user_ids == [2, 3]
