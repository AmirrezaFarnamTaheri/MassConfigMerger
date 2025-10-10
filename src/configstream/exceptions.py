# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

"""Custom exception types for the ConfigStream application."""


class ConfigStreamError(Exception):
    """Base exception class for all application-specific errors."""

    pass


class GistUploadError(ConfigStreamError):
    """Raised for errors during GitHub Gist uploads."""

    pass


class ParserError(ConfigStreamError):
    """Raised for errors during configuration parsing."""

    pass


class NetworkError(ConfigStreamError):
    """Raised for network-related errors, such as connection or timeout issues."""

    pass


class ConfigError(ConfigStreamError):
    """Raised for configuration-related errors."""

    pass
