import logging
import re


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive information in logs"""

    PATTERNS = {
        "uuid": r"(?:id|uuid|password|token)\s*[=:]\s*[a-f0-9\-]{32,}",
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "ip": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "url": r"(?:https?://)[^\s]+",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()

        # Mask UUIDs and passwords
        message = re.sub(self.PATTERNS["uuid"], "[MASKED_CREDENTIAL]", message, flags=re.IGNORECASE)

        # Mask emails
        message = re.sub(self.PATTERNS["email"], "[MASKED_EMAIL]", message)

        # Keep IPs for debugging but could mask if needed
        # message = re.sub(self.PATTERNS['ip'], '[MASKED_IP]', message)

        record.msg = message
        return True


def setup_logging(log_level: str = "INFO", mask_sensitive: bool = True):
    """Setup logging with optional sensitive data filtering"""

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Add new handlers
    file_handler = logging.FileHandler("configstream.log")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # Add filter if requested
    if mask_sensitive:
        # Avoid adding filter if it already exists
        if not any(isinstance(f, SensitiveDataFilter) for f in root_logger.filters):
            root_logger.addFilter(SensitiveDataFilter())
