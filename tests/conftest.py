import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--run-paid", action="store_true", default=False, help="run paid tests"
    )