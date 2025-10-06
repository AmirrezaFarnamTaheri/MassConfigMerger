from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List, Optional

from pydantic import Field, field_validator

from .base import BaseConfig


class TelegramSettings(BaseConfig):
    """Settings for Telegram integration."""

    api_id: Optional[int] = Field(None, description="Your Telegram API ID from my.telegram.org.")
    api_hash: Optional[str] = Field(None, description="Your Telegram API hash from my.telegram.org.")
    bot_token: Optional[str] = Field(None, description="Your Telegram bot token for bot mode, from @BotFather.")
    allowed_user_ids: List[int] = Field(
        default_factory=list,
        description="List of numeric Telegram user IDs allowed to interact with the bot.",
    )
    session_path: Path = Field(
        "user.session", description="Path to the Telethon session file."
    )

    @field_validator("allowed_user_ids", mode="before")
    @classmethod
    def _parse_allowed_ids(cls, value: Any) -> list[int]:
        """Parse a string or int of user IDs into a list of integers."""
        if isinstance(value, str):
            try:
                return [int(v) for v in re.split(r"[\s,]+", value.strip()) if v]
            except ValueError as exc:
                raise ValueError("allowed_user_ids must be a list of integers") from exc
        if isinstance(value, int):
            return [value]
        return value