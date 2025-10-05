import yaml
from pathlib import Path
from massconfigmerger.core.config_loader import load_config

def test_load_defaults(tmp_path):
    """Test that default settings are loaded correctly."""
    p = tmp_path / "config.yaml"
    p.write_text("{}")
    loaded = load_config(p)
    assert loaded.output.output_dir == Path("output")
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
    assert loaded.output.output_dir == Path("/tmp/test")
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


from unittest.mock import patch
from massconfigmerger.config import Settings
from massconfigmerger.core.config_loader import YamlConfigSettingsSource
from pydantic.fields import FieldInfo

def test_yaml_source_invalid_file(tmp_path):
    """Test that YamlConfigSettingsSource handles an invalid YAML file."""
    p = tmp_path / "invalid.yaml"
    p.write_text("this is not a valid yaml file: [")

    source = YamlConfigSettingsSource(settings_cls=Settings, yaml_file=p)

    # Test __call__ method
    assert source() == {}

    # Test get_field_value method
    assert source.get_field_value(FieldInfo(), "any_field") is None


def test_load_config_auto_discovery(fs):
    """Test that load_config finds config.yaml in the project root."""
    fs.create_file("/app/pyproject.toml")
    fs.create_file("/app/config.yaml", contents='network:\n  concurrent_limit: 100')

    with patch('pathlib.Path.cwd', return_value=Path('/app')):
        settings = load_config()
        assert settings.network.concurrent_limit == 100


def test_load_config_no_project_root(fs, caplog):
    """Test load_config when pyproject.toml is not found."""
    fs.create_dir("/app")
    with patch('pathlib.Path.cwd', return_value=Path('/app')):
        settings = load_config()
        assert settings.network.concurrent_limit == 20 # a default value
        assert "Could not find project root marker" in caplog.text