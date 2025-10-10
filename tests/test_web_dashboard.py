import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from configstream.config import Settings, OutputSettings
from configstream.web_dashboard import create_app, DashboardData


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
def app(settings: Settings):
    """Fixture for a Flask app instance."""
    app = create_app(settings=settings)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Fixture for a Flask test client."""
    with app.test_client() as client:
        yield client


def test_get_current_results_no_file(settings: Settings):
    """Test get_current_results when the data file does not exist."""
    dashboard_data = DashboardData(settings)
    results = dashboard_data.get_current_results()
    assert results == {"timestamp": None, "nodes": []}


def test_get_history_filtering(settings: Settings):
    """Test get_history to ensure it correctly filters by time."""
    dashboard_data = DashboardData(settings)
    now = datetime.now()
    old_ts = (now - timedelta(hours=30)).isoformat()
    new_ts = (now - timedelta(hours=1)).isoformat()
    history_file = dashboard_data.history_file
    with open(history_file, "w") as f:
        f.write(json.dumps({"timestamp": old_ts, "nodes": []}) + "\n")
        f.write(json.dumps({"timestamp": new_ts, "nodes": []}) + "\n")

    history = dashboard_data.get_history(hours=24)
    assert len(history) == 1
    assert history[0]["timestamp"] == new_ts


def test_api_current_endpoint(client, settings: Settings):
    """Test the /api/current endpoint."""
    test_data = {"timestamp": datetime.now().isoformat(), "nodes": [{"protocol": "VLESS"}]}
    settings.output.current_results_file.write_text(json.dumps(test_data))

    response = client.get("/api/current")
    assert response.status_code == 200
    json_response = response.get_json()
    assert json_response["nodes"][0]["protocol"] == "VLESS"


def test_api_export_csv(client, settings: Settings):
    """Test the CSV export functionality."""
    nodes = [{"protocol": "vless", "country": "US", "ping_ms": 100}]
    test_data = {"timestamp": datetime.now().isoformat(), "nodes": nodes}
    settings.output.current_results_file.write_text(json.dumps(test_data))

    response = client.get("/api/export/csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    # Normalize line endings and check for content
    data = response.data.decode().replace("\r\n", "\n")
    assert "country,ping_ms,protocol" in data
    assert "US,100,vless" in data


def test_api_export_unsupported_format(client):
    """Test that an unsupported export format returns an error."""
    response = client.get("/api/export/xml")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Unsupported format"}