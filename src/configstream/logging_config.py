import logging
import re
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive information in logs"""

    PATTERNS = {
        'uuid': r'(?:id|uuid|password|token)\s*[=:]\s*[a-f0-9\-]{32,}',
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'ip': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'url': r'(?:https?://)[^\s]+',
    }

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()

        # Mask UUIDs and passwords
        message = re.sub(
            self.PATTERNS['uuid'],
            '[MASKED_CREDENTIAL]',
            message,
            flags=re.IGNORECASE
        )

        # Mask emails
        message = re.sub(
            self.PATTERNS['email'],
            '[MASKED_EMAIL]',
            message
        )

        # Keep IPs for debugging but could mask if needed
        # message = re.sub(self.PATTERNS['ip'], '[MASKED_IP]', message)

        record.msg = message
        return True


def setup_logging(log_level: str = 'INFO', mask_sensitive: bool = True):
    """Setup logging with optional sensitive data filtering"""

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('configstream.log'),
            logging.StreamHandler()
        ]
    )

    if mask_sensitive:
        logger = logging.getLogger()
        logger.addFilter(SensitiveDataFilter())