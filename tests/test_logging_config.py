import logging

import pytest

from configstream.logging_config import SensitiveDataFilter, setup_logging


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test."""
    logging.getLogger().manager.loggerDict.clear()
    root = logging.getLogger()
    root.handlers = []
    root.filters = []
    root.setLevel(logging.WARNING)  # a default level


@pytest.fixture
def log_record():
    return logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="",
        args=(),
        exc_info=None,
    )


def test_sensitive_data_filter_masks_uuid(log_record):
    log_record.msg = "User with id=a1b2c3d4-e5f6-7890-1234-567890abcdef tried to login"
    filtr = SensitiveDataFilter()
    filtr.filter(log_record)
    assert "MASKED_CREDENTIAL" in log_record.msg
    assert "a1b2c3d4" not in log_record.msg


def test_sensitive_data_filter_masks_email(log_record):
    log_record.msg = "Contact us at test@example.com for more info"
    filtr = SensitiveDataFilter()
    filtr.filter(log_record)
    assert "MASKED_EMAIL" in log_record.msg
    assert "test@example.com" not in log_record.msg


def test_sensitive_data_filter_ignores_ip(log_record):
    log_record.msg = "Connecting to 192.168.1.1"
    filtr = SensitiveDataFilter()
    filtr.filter(log_record)
    assert "192.168.1.1" in log_record.msg


def test_setup_logging_applies_filter():
    setup_logging(mask_sensitive=True)
    logger = logging.getLogger()
    assert any(isinstance(f, SensitiveDataFilter) for f in logger.filters)


def test_setup_logging_does_not_apply_filter():
    setup_logging(mask_sensitive=False)
    logger = logging.getLogger()
    assert not any(isinstance(f, SensitiveDataFilter) for f in logger.filters)


def test_setup_logging_sets_level():
    setup_logging(log_level="DEBUG")
    logger = logging.getLogger()
    assert logger.level == logging.DEBUG
