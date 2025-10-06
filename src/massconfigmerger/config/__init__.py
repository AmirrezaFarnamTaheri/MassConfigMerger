from __future__ import annotations

from pathlib import Path
from typing import Optional, Type

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from .filtering import FilteringSettings
from .loader import YamlConfigSettingsSource, load_config
from .network import NetworkSettings
from .output import OutputSettings
from .processing import ProcessingSettings
from .security import SecuritySettings
from .telegram import TelegramSettings


class Settings(BaseSettings):
    """
    Main application configuration model.
    """

    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    network: NetworkSettings = Field(default_factory=NetworkSettings)
    filtering: FilteringSettings = Field(default_factory=FilteringSettings)
    output: OutputSettings = Field(default_factory=OutputSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    config_file: Optional[Path] = Field(default=None, exclude=True)

    model_config = SettingsConfigDict(
        env_prefix="", case_sensitive=False, env_nested_delimiter="__"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        config_file = init_settings.init_kwargs.get("config_file")
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file=config_file),
            file_secret_settings,
        )


__all__ = [
    "Settings",
    "TelegramSettings",
    "NetworkSettings",
    "FilteringSettings",
    "OutputSettings",
    "ProcessingSettings",
    "SecuritySettings",
    "load_config",
]