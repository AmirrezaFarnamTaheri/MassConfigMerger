from __future__ import annotations

import pytest
from massconfigmerger.config import TelegramSettings
from pydantic import ValidationError

def test_telegram_settings_parse_allowed_ids_invalid_type():
    """Test that a ValueError is raised for an invalid type."""
    with pytest.raises(ValidationError):
        TelegramSettings(allowed_user_ids="not a list or int")