"""Configuration loading utilities for MassConfigMerger.

This module provides the necessary components to load application settings
from a YAML file, complementing Pydantic's default environment variable
and dotenv support. It defines a custom settings source, `YamlConfigSettingsSource`,
which reads a specified YAML file, and a `load_config` function that
orchestrates the entire loading process.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Type

import yaml
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from ..config import Settings
from .file_utils import find_project_root


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """
    A Pydantic settings source that loads variables from a YAML file.

    This class extends Pydantic's settings management capabilities to allow
    for configuration values to be read directly from a YAML file. It is
    designed to be used within the `Settings.settings_customise_sources`
    classmethod.
    """

    def __init__(self, settings_cls: Type[BaseSettings], yaml_file: Path | None):
        """
        Initialize the YAML settings source.

        Args:
            settings_cls: The Pydantic `BaseSettings` class to load.
            yaml_file: The path to the YAML configuration file.
        """
        super().__init__(settings_cls)
        self.yaml_file = yaml_file

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str] | None:
        """
        Get a value for a specific field from the YAML file.

        Pydantic calls this method for each field in the settings model.

        Args:
            field: The Pydantic field being processed.
            field_name: The name of the field.

        Returns:
            A tuple containing the loaded value and the field name, or None
            if the file does not exist or the field is not present.
        """
        if not self.yaml_file or not self.yaml_file.exists():
            return None
        try:
            yaml_data = yaml.safe_load(self.yaml_file.read_text()) or {}
            field_value = yaml_data.get(field_name)
            return field_value, field_name
        except (yaml.YAMLError, IOError):
            return None

    def __call__(self) -> dict[str, Any]:
        """
        Load all settings from the YAML file.

        This method is called by Pydantic to get all settings from this
        source at once.

        Returns:
            A dictionary of settings loaded from the YAML file, or an
            empty dictionary if the file cannot be read.
        """
        if not self.yaml_file or not self.yaml_file.exists():
            return {}
        try:
            return yaml.safe_load(self.yaml_file.read_text()) or {}
        except (yaml.YAMLError, IOError):
            return {}


def load_config(path: Path | None = None) -> Settings:
    """
    Load application settings from a YAML file and environment variables.

    This function serves as the main entry point for loading configuration.
    It automatically searches for a `config.yaml` file in the project root
    if no explicit path is provided. The settings are loaded in a layered
    manner, with environment variables taking precedence over the YAML file.

    Args:
        path: An optional path to a YAML configuration file. If not provided,
              the function will search for `config.yaml` in the project root.

    Returns:
        A populated `Settings` object containing the application's configuration.
    """
    config_file = path
    if config_file is None:
        try:
            project_root = find_project_root()
            default_config_path = project_root / "config.yaml"
            if default_config_path.exists():
                config_file = default_config_path
        except FileNotFoundError:
            logging.warning(
                "Could not find project root marker 'pyproject.toml'. "
                "Default 'config.yaml' will not be loaded."
            )
    return Settings(config_file=config_file)