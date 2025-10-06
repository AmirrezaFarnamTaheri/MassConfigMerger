from __future__ import annotations

from typing import Optional

from pydantic import Field

from .base import BaseConfig


class SecuritySettings(BaseConfig):
    """Settings for security-related features like blocklist checking."""

    apivoid_api_key: Optional[str] = Field(
        None, description="API key for APIVoid IP Reputation API."
    )
    blocklist_detection_threshold: int = Field(
        1,
        description="Number of blacklist detections required to consider an IP malicious. 0 to disable.",
    )