from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from massconfigmerger.config import (
    Settings,
    TelegramSettings,
    YamlConfigSettingsSource,
    load_config,
)


def test_telegram_settings_parse_allowed_ids():
    """Test parsing of allowed_user_ids in TelegramSettings."""
    # From comma-separated string
    settings = TelegramSettings(allowed_user_ids="123, 456")
    assert settings.allowed_user_ids == [123, 456]

    # From space-separated string
    settings = TelegramSettings(allowed_user_ids="123 456")
    assert settings.allowed_user_ids == [123, 456]

    # From a single integer
    settings = TelegramSettings(allowed_user_ids=123)
    assert settings.allowed_user_ids == [123]

    # From a list of integers (should pass through)
    settings = TelegramSettings(allowed_user_ids=[123, 456])
    assert settings.allowed_user_ids == [123, 456]

    # Test invalid value
    with pytest.raises(ValidationError) as exc_info:
        TelegramSettings(allowed_user_ids="123,abc")
    assert "allowed_user_ids must be a list of integers" in str(exc_info.value)


def test_yaml_config_source_file_not_found():
    """Test YamlConfigSettingsSource when the config file does not exist."""
    source = YamlConfigSettingsSource(Settings, Path("nonexistent.yaml"))
    assert source.get_field_value(None, "field") is None
    assert source() == {}


def test_yaml_config_source_invalid_yaml(tmp_path: Path):
    """Test YamlConfigSettingsSource with a malformed YAML file."""
    p = tmp_path / "invalid.yaml"
    p.write_text("key: value: nested")
    source = YamlConfigSettingsSource(Settings, p)
    assert source.get_field_value(None, "field") is None
    assert source() == {}


def test_load_config_no_project_root(monkeypatch):
    """Test load_config when find_project_root raises FileNotFoundError."""
    from massconfigmerger.constants import CONFIG_FILE_NAME

    monkeypatch.setattr(
        "massconfigmerger.config.find_project_root",
        lambda: (_ for _ in ()).throw(FileNotFoundError),
    )
    with patch("massconfigmerger.config.logging.warning") as mock_warning:
        settings = load_config()
        assert isinstance(settings, Settings)
        mock_warning.assert_called_once_with(
            "Could not find project root marker 'pyproject.toml'. "
            "Default '%s' will not be loaded.",
            CONFIG_FILE_NAME,
        )


def test_load_config_with_yaml(tmp_path: Path):
    """Test that settings are loaded correctly from a YAML file."""
    config_content = {
        "network": {"request_timeout": 50},
        "telegram": {"api_id": 999},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_content, f)

    settings = load_config(config_path)
    assert settings.network.request_timeout == 50
    assert settings.telegram.api_id == 999


def test_load_config_finds_default_config(fs):
    """Test that load_config finds and loads a default config.yaml."""
    # Create a fake project structure
    fs.create_file("pyproject.toml", contents="")
    fs.create_file("config.yaml", contents="network:\n  request_timeout: 99")

    settings = load_config()
    assert settings.network.request_timeout == 99


@pytest.mark.parametrize(
    "path_field, malicious_path",
    [
        ("output_dir", "/etc/passwd"),
        ("output_dir", "../../../../etc/passwd"),
        ("log_dir", "/var/log"),
        ("log_dir", "../../var/log"),
        ("history_db_file", "/root/.bash_history"),
        ("history_db_file", "../.bash_history"),
        ("surge_file", "/tmp/test.conf"),
        ("qx_file", "../../../tmp/test.conf"),
    ],
)
def test_output_settings_path_traversal_prevention(path_field, malicious_path):
    """Test that path traversal attempts are blocked in OutputSettings."""
    from massconfigmerger.config import OutputSettings

    with pytest.raises(ValidationError) as exc_info:
        OutputSettings(**{path_field: malicious_path})

    assert "Path cannot be absolute or contain '..'" in str(exc_info.value)


def test_output_settings_valid_paths():
    """Test that valid relative paths are accepted in OutputSettings."""
    from massconfigmerger.config import OutputSettings

    try:
        settings = OutputSettings(
            output_dir="my_output",
            log_dir="my_logs",
            history_db_file="data/history.db",
            surge_file="surge.conf",
        )
        assert settings.output_dir == Path("my_output")
        assert settings.log_dir == Path("my_logs")
        assert settings.history_db_file == Path("data/history.db")
        assert settings.surge_file == Path("surge.conf")
    except ValidationError as e:
        pytest.fail(f"Valid paths raised a ValidationError unexpectedly: {e}")