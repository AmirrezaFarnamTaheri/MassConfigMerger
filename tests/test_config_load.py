import yaml
from pathlib import Path
from massconfigmerger.config import load_config

def test_load_defaults(tmp_path):
    """Test that default settings are loaded correctly."""
    p = tmp_path / "config.yaml"
    p.write_text("{}")
    loaded = load_config(p)
    assert loaded.output.output_dir == "output"
    assert loaded.network.concurrent_limit == 20
    assert loaded.telegram.api_id is None

def test_load_custom_values(tmp_path):
    """Test that custom values from a YAML file override defaults."""
    p = tmp_path / "config.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "output": {"output_dir": "/tmp/test"},
                "network": {"concurrent_limit": 50},
                "telegram": {"api_id": 12345},
            }
        )
    )
    loaded = load_config(p)
    assert loaded.output.output_dir == "/tmp/test"
    assert loaded.network.concurrent_limit == 50
    assert loaded.telegram.api_id == 12345

def test_load_invalid_yaml_uses_defaults(tmp_path):
    """Test that an invalid YAML file results in default settings."""
    p = tmp_path / "bad.yaml"
    p.write_text(": { invalid }")
    settings = load_config(p)
    assert settings.network.concurrent_limit == 20
    assert settings.telegram.api_id is None

def test_file_not_found_uses_defaults():
    """Test that a missing config file results in default settings."""
    missing = Path("non_existent_config.yaml")
    settings = load_config(missing)
    assert settings.network.concurrent_limit == 20

def test_env_variable_override(tmp_path, monkeypatch):
    """Test that environment variables override YAML settings."""
    p = tmp_path / "config.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "telegram": {"api_id": 123},
                "network": {"request_timeout": 5},
            }
        )
    )
    monkeypatch.setenv("telegram__api_id", "54321")
    monkeypatch.setenv("network__request_timeout", "15")

    loaded = load_config(p)
    assert loaded.telegram.api_id == 54321
    assert loaded.network.request_timeout == 15

def test_allowed_user_ids_validation(tmp_path):
    """Test validation and parsing of allowed_user_ids."""
    p = tmp_path / "config.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "telegram": {"allowed_user_ids": "1, 2,3, 4 ,5"}
            }
        )
    )
    loaded = load_config(p)
    assert loaded.telegram.allowed_user_ids == [1, 2, 3, 4, 5]

    p.write_text(yaml.safe_dump({"telegram": {"allowed_user_ids": 12345}}))
    loaded = load_config(p)
    assert loaded.telegram.allowed_user_ids == [12345]