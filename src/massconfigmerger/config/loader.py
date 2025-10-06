from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Type

import yaml
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from ..constants import CONFIG_FILE_NAME
from ..core.file_utils import find_project_root


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """
    A Pydantic settings source that loads variables from a YAML file.
    """

    def __init__(self, settings_cls: Type[BaseSettings], yaml_file: Path | None):
        super().__init__(settings_cls)
        self.yaml_file = yaml_file
        self._data: dict[str, Any] | None = None
        if self.yaml_file and self.yaml_file.exists():
            try:
                self._data = yaml.safe_load(self.yaml_file.read_text()) or {}
            except (yaml.YAMLError, IOError):
                self._data = {}
        else:
            self._data = {}

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str] | None:
        if not self._data:
            return None
        return (self._data.get(field_name), field_name)

    def __call__(self) -> dict[str, Any]:
        return dict(self._data or {})


def load_config(path: Path | None = None) -> "Settings":
    """
    Load application settings from a YAML file and environment variables.
    """
    from . import Settings

    config_file = path
    if config_file is None:
        try:
            project_root = find_project_root()
            default_config_path = project_root / CONFIG_FILE_NAME
            if default_config_path.exists():
                config_file = default_config_path
        except FileNotFoundError:
            logging.warning(
                "Could not find project root marker 'pyproject.toml'. "
                "Default '%s' will not be loaded.",
                CONFIG_FILE_NAME,
            )
    return Settings(config_file=config_file)