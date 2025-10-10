import pytest
from pathlib import Path
from configstream.config import Settings, OutputSettings
from configstream.core.types import ConfigResult

def pytest_addoption(parser):
    parser.addoption(
        "--run-paid", action="store_true", default=False, help="run paid tests"
    )

@pytest.fixture
def settings(tmp_path: Path, monkeypatch) -> Settings:
    """Fixture for a Settings object with a temporary data directory."""
    monkeypatch.chdir(tmp_path)
    data_dir = Path("data")
    data_dir.mkdir()
    settings = Settings()
    settings.output = OutputSettings(
        current_results_file=data_dir / "current_results.json",
        history_file=data_dir / "history.jsonl",
        output_dir=data_dir,
    )
    return settings

@pytest.fixture
def config_result() -> ConfigResult:
    """Fixture for a sample ConfigResult object."""
    return ConfigResult(
        config="vless://test",
        protocol="VLESS",
        ping_time=100.0,
        country="US",
        host="1.1.1.1",
        port=443,
        is_blocked=False,
        isp="Test Org",
        is_reachable=True,
    )

@pytest.fixture
def app(settings: Settings):
    """Fixture for a Flask app instance."""
    from configstream.web_dashboard import create_app
    app = create_app(settings=settings)
    app.config["TESTING"] = True
    return app

@pytest.fixture
def client(app):
    """Fixture for a Flask test client."""
    with app.test_client() as client:
        yield client