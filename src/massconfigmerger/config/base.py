from __future__ import annotations

from pydantic import BaseModel


class BaseConfig(BaseModel):
    """Base configuration with common settings."""

    class Config:
        extra = "forbid"
        validate_assignment = True