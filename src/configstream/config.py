from __future__ import annotations

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Main application configuration model.
    """

    sources: List[str] = Field(
        default_factory=list,
        description="Comma-separated URLs of subscription sources.",
    )
    test_timeout: int = Field(5, description="Timeout in seconds for testing each proxy.")
    test_max_workers: int = Field(
        10, description="Maximum number of concurrent workers for testing proxies."
    )
    output_dir: str = Field("output", description="Directory to save the output files.")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CONFIGSTREAM_",
        case_sensitive=False,
        env_nested_delimiter="__",
    )


settings = Settings()  # type: ignore
