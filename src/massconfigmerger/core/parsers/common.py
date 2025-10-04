from __future__ import annotations

import base64
import binascii
import json
from typing import Any


def sanitize_str(value: Any) -> Any:
    """Strip whitespace and remove newlines from string values."""
    if isinstance(value, str):
        return value.strip().replace("\n", "").replace("\r", "")
    return value


def sanitize_headers(headers_data: Any) -> Any:
    """Sanitize ws-headers, which can be a dict, a JSON string, or a base64-encoded JSON string."""
    if not headers_data:
        return None

    headers = headers_data
    if isinstance(headers_data, str):
        try:
            # Attempt to decode from base64, then parse JSON
            padded = headers_data + "=" * (-len(headers_data) % 4)
            decoded_json = base64.urlsafe_b64decode(padded).decode()
            headers = json.loads(decoded_json)
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
            try:
                # If not base64, maybe it's a plain JSON string
                headers = json.loads(headers_data)
            except (json.JSONDecodeError, TypeError):
                # Otherwise, treat as a plain string
                pass

    if isinstance(headers, dict):
        return {
            sanitize_str(k): sanitize_str(v)
            for k, v in headers.items()
        }

    return sanitize_str(headers)