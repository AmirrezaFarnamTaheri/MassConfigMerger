from .config import Settings, load_settings

try:
    settings = load_settings()
except ValueError:
    settings = Settings()

__all__ = ["Settings", "load_settings", "settings"]
