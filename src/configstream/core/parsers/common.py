from __future__ import annotations

import base64
import binascii
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseParser(ABC):
    """Abstract base class for all protocol parsers."""

    def __init__(self, config_uri: str):
        self.config_uri = config_uri

    @abstractmethod
    def parse(self) -> Optional[Dict[str, Any]]:
        """Parse the configuration URI and return a dictionary of parameters."""
        raise NotImplementedError

    def get_identifier(self) -> Optional[str]:
        """
        Return a unique identifier for the proxy configuration,
        typically a user ID, password, or other secret.
        This is used for semantic hashing.
        """
        return None

    @staticmethod
    def sanitize_str(value: Any) -> Any:
        """Strip whitespace and remove newlines from string values."""
        if isinstance(value, str):
            return value.strip().replace("\n", "").replace("\r", "")
        return value

    @staticmethod
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
                BaseParser.sanitize_str(k): BaseParser.sanitize_str(v)
                for k, v in headers.items()
            }
        if isinstance(headers, str) and ":" in headers:
            key, value = headers.split(":", 1)
            return {BaseParser.sanitize_str(key): BaseParser.sanitize_str(value)}

        return BaseParser.sanitize_str(headers)
