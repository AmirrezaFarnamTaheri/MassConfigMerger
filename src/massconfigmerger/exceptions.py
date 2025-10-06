"""Custom exception types for the MassConfigMerger application."""


class MassConfigMergerError(Exception):
    """Base exception class for all application-specific errors."""

    pass


class GistUploadError(MassConfigMergerError):
    """Raised for errors during GitHub Gist uploads."""

    pass


class ParserError(MassConfigMergerError):
    """Raised for errors during configuration parsing."""

    pass


class NetworkError(MassConfigMergerError):
    """Raised for network-related errors, such as connection or timeout issues."""

    pass


class ConfigError(MassConfigMergerError):
    """Raised for configuration-related errors."""

    pass