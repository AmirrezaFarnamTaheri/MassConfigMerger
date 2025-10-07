from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from configstream.config import Settings
from configstream.web import app




@patch("configstream.web.run_aggregation_pipeline", new_callable=AsyncMock)
@patch("configstream.web.load_config")
def test_aggregate_api(mock_load_config, mock_run_pipeline, client, fs):
    """Test the /api/aggregate route."""

    fs.create_file("config.yaml")
    mock_load_config.return_value = Settings()
    mock_run_pipeline.return_value = (Path("/fake/dir"), [Path("/fake/dir/file.txt")])

    response = client.post("/api/aggregate", json={})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["output_dir"] == "/fake/dir"
    assert payload["file_count"] == 1
    assert payload["files"] == ["/fake/dir/file.txt"]
    mock_run_pipeline.assert_awaited_once()


@patch("configstream.web.run_aggregation_pipeline", new_callable=AsyncMock)
@patch("configstream.web.load_config")
def test_aggregate_requires_token(mock_load_config, mock_run_pipeline, client, fs):
    """Ensure /api/aggregate enforces the configured API token."""

    settings = Settings()
    settings.security.web_api_token = "topsecret"
    mock_load_config.return_value = settings

    response = client.post("/api/aggregate", json={})

    assert response.status_code == 401
    assert b"Missing or invalid API token" in response.data
    mock_run_pipeline.assert_not_awaited()

    mock_run_pipeline.reset_mock()
    mock_run_pipeline.return_value = (Path("/secured"), [])
    response_ok = client.post(
        "/api/aggregate",
        json={},
        headers={"X-API-Key": "topsecret"},
    )

    assert response_ok.status_code == 200
    mock_run_pipeline.assert_awaited_once()


@patch("configstream.web.run_merger_pipeline", new_callable=AsyncMock)
@patch("configstream.web.load_config")
def test_merge_route_success(mock_load_config, mock_run_merger, client, fs):
    """Test the /api/merge route when the resume file exists."""

    fs.create_file("pyproject.toml")
    fs.create_dir("fake_output")
    fs.create_file("fake_output/vpn_subscription_raw.txt")
    settings = Settings()
    settings.output.output_dir = Path("fake_output")
    mock_load_config.return_value = settings

    response = client.post("/api/merge", json={})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "merge complete"
    assert payload["resume_file"].endswith("vpn_subscription_raw.txt")
    mock_run_merger.assert_awaited_once()


@patch("configstream.web.run_merger_pipeline", new_callable=AsyncMock)
@patch("configstream.web.load_config")
def test_merge_route_no_resume_file(mock_load_config, mock_run_merger, client, fs):
    """Test the /api/merge route when the resume file is missing."""

    fs.create_file("pyproject.toml")
    settings = Settings()
    settings.output.output_dir = Path("fake_output")
    mock_load_config.return_value = settings

    response = client.post("/api/merge", json={})

    assert response.status_code == 404
    assert "error" in response.get_json()
    mock_run_merger.assert_not_awaited()


@patch("configstream.web.run_merger_pipeline", new_callable=AsyncMock)
@patch("configstream.web.load_config")
def test_merge_requires_token(mock_load_config, mock_run_merger, client, fs):
    """Ensure /api/merge enforces the configured API token."""

    fs.create_file("pyproject.toml")
    fs.create_dir("fake_output")
    fs.create_file("fake_output/vpn_subscription_raw.txt")
    settings = Settings()
    settings.output.output_dir = Path("fake_output")
    settings.security.web_api_token = "supersecret"
    mock_load_config.return_value = settings

    response = client.post("/api/merge", json={})

    assert response.status_code == 401
    assert b"Missing or invalid API token" in response.data
    mock_run_merger.assert_not_awaited()

    mock_run_merger.reset_mock()
    response_ok = client.post(
        "/api/merge",
        json={},
        headers={"Authorization": "Bearer supersecret"},
    )

    assert response_ok.status_code == 200
    mock_run_merger.assert_awaited_once()


def test_report_route_html(client, fs):
    """Test the /report route when an HTML report exists."""
    fs.create_file("pyproject.toml")
    fs.create_file("config.yaml", contents="output:\n  output_dir: 'fake_output'")
    fs.create_dir("fake_output")
    fs.create_file("fake_output/vpn_report.html", contents=b"<h1>HTML Report</h1>")

    response = client.get("/report")

    assert response.status_code == 200
    assert response.data == b"<h1>HTML Report</h1>"


@patch("configstream.web.find_project_root", side_effect=FileNotFoundError)
def test_get_root_fallback(mock_find_root, client, fs):
    """Test _get_root fallback when pyproject.toml is not found."""
    # No pyproject.toml and find_project_root raises error
    fs.create_file("config.yaml", contents="output:\n  output_dir: 'fake_output'")
    fs.create_dir("fake_output")
    fs.create_file("fake_output/vpn_report.html", contents=b"<h1>Fallback Report</h1>")

    response = client.get("/report")
    assert response.status_code == 200
    assert response.data == b"<h1>Fallback Report</h1>"


def test_report_route_json(client, fs):
    """Test the /report route when only a JSON report exists."""
    fs.create_file("pyproject.toml")
    fs.create_file("config.yaml", contents="output:\n  output_dir: 'fake_output'")
    fs.create_dir("fake_output")
    fs.create_file("fake_output/vpn_report.json", contents='{"key": "value"}')

    response = client.get("/report")

    assert response.status_code == 200
    assert "<h1>VPN Report</h1>" in response.data.decode()
    assert '&#34;key&#34;: &#34;value&#34;' in response.data.decode()


def test_report_route_not_found(client, fs):
    """Test the /report route when no report is found."""
    fs.create_file("pyproject.toml")
    fs.create_file("config.yaml", contents="output:\n  output_dir: 'fake_output'")
    fs.create_dir("fake_output")

    response = client.get("/report")

    assert response.status_code == 404
    assert b"Report not found" in response.data


@patch("configstream.web.app.run")
def test_main_run(mock_run):
    """Test that the main function calls app.run."""
    from configstream.web import main
    main()
    mock_run.assert_called_once_with(host="0.0.0.0", port=8080, debug=False)


def test_index_route(client):
    """Test the index route."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"ConfigStream Control Panel" in response.data


@patch("configstream.web._run_async_task")
def test_index_route_history_exception(mock_run_async, client, fs):
    """Test the index route when loading history fails."""
    fs.create_file("pyproject.toml")
    fs.create_file("config.yaml", contents="output:\n  history_db_file: 'fake.db'")
    mock_run_async.side_effect = Exception("DB fail")

    response = client.get("/")
    assert response.status_code == 200
    assert b"No proxy history recorded yet." in response.data


def test_health_check_route(client):
    """Test the /health route."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


@patch("configstream.web.Database")
def test_history_route_success(MockDatabase, client, fs):
    """Test the /history route with successful data retrieval."""
    fs.create_file("pyproject.toml")
    fs.create_file("config.yaml", contents="output:\n  history_db_file: 'fake.db'")
    fs.create_dir("output")


    mock_db_instance = MockDatabase.return_value
    mock_db_instance.connect = AsyncMock()
    mock_db_instance.close = AsyncMock()
    mock_db_instance.get_proxy_history = AsyncMock(return_value={
        "proxy1": {"successes": 10, "failures": 0, "last_tested": 1672531200},
        "proxy2": {"successes": 5, "failures": 5, "last_tested": "1672531201"},
        "proxy3": {"successes": 0, "failures": 10, "last_tested": "invalid-ts"},
        "proxy4": {"successes": 1, "failures": 0},
    })

    response = client.get("/history")

    assert response.status_code == 200
    data = response.data.decode()

    # Check that the data is sorted by reliability and summary values render
    assert "📊 Total Tracked: 4" in data
    assert "✅ Healthy: 2" in data
    assert "⚠️ Critical: 1" in data
    p1 = data.index("proxy1")
    p4 = data.index("proxy4")
    p2 = data.index("proxy2")
    p3 = data.index("proxy3")
    assert p1 < p4 < p2 < p3

    # Check for correct data rendering
    assert "100.00%" in data
    assert "50.00%" in data
    assert "0.00%" in data
    assert "2023-01-01 00:00:00" in data
    assert "N/A" in data

    mock_db_instance.connect.assert_awaited_once()
    mock_db_instance.get_proxy_history.assert_awaited_once()
    mock_db_instance.close.assert_awaited_once()


@patch("configstream.web.Database")
def test_history_route_empty(MockDatabase, client, fs):
    """Test the /history route with no data."""
    fs.create_file("pyproject.toml")
    fs.create_file("config.yaml", contents="output:\n  history_db_file: 'fake.db'")
    fs.create_dir("output")
    mock_db_instance = MockDatabase.return_value
    mock_db_instance.connect = AsyncMock()
    mock_db_instance.close = AsyncMock()
    mock_db_instance.get_proxy_history = AsyncMock(return_value={})

    response = client.get("/history")
    assert response.status_code == 200
    assert b"No proxy history recorded yet." in response.data


@patch("configstream.web.Database")
def test_history_route_bad_data(MockDatabase, client, fs):
    """Test the /history route with malformed data in the database."""
    fs.create_file("pyproject.toml")
    fs.create_file("config.yaml", contents="output:\n  history_db_file: 'fake.db'")
    fs.create_dir("output")

    mock_db_instance = MockDatabase.return_value
    mock_db_instance.connect = AsyncMock()
    mock_db_instance.close = AsyncMock()
    mock_db_instance.get_proxy_history = AsyncMock(return_value={
        "proxy1": {"successes": "not-a-number", "failures": 1},
    })

    response = client.get("/history")
    assert response.status_code == 200
    # Check that it gracefully handles the bad data and shows 0.00%
    assert b"0.00%" in response.data


@patch("configstream.web.Database")
def test_history_api_endpoint(MockDatabase, client, fs):
    """Test the JSON API for proxy history."""

    fs.create_file("pyproject.toml")
    fs.create_file("config.yaml", contents="output:\n  history_db_file: 'fake.db'")
    fs.create_dir("output")

    mock_db_instance = MockDatabase.return_value
    mock_db_instance.connect = AsyncMock()
    mock_db_instance.close = AsyncMock()
    mock_db_instance.get_proxy_history = AsyncMock(
        return_value={
            "proxy1": {"successes": 3, "failures": 1, "last_tested": 1672531200},
            "proxy2": {"successes": 0, "failures": 2},
            "proxy3": {"successes": 1, "failures": 0},
        }
    )

    response = client.get("/api/history?limit=2")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["returned"] == 2
    assert payload["total"] == 3
    assert payload["healthy"] >= 1
    assert any(item["key"] == "proxy1" for item in payload["items"])


def test_metrics_route(client):
    """Test the /metrics route."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"python_info" in response.data


@patch("configstream.web.run_aggregation_pipeline", new_callable=AsyncMock)
@patch("configstream.web.load_config")
def test_aggregate_route_exception(mock_load_config, mock_run_pipeline, client, fs):
    """Test the /api/aggregate route when an exception occurs."""

    fs.create_file("config.yaml")
    mock_load_config.return_value = Settings()
    mock_run_pipeline.side_effect = Exception("Test exception")

    response = client.post("/api/aggregate", json={})

    assert response.status_code == 500
    assert response.get_json()["error"] == "Test exception"


def test_report_route_no_project_root(client, fs):
    """Test the /report route when pyproject.toml is not found."""
    # Do not create pyproject.toml to simulate a non-project environment
    fs.create_file("config.yaml", contents="output:\n  output_dir: 'fake_output'")
    fs.create_dir("fake_output")
    fs.create_file("fake_output/vpn_report.html", contents=b"<h1>HTML Report</h1>")

    # The application should fall back to the current working directory
    response = client.get("/report")

    assert response.status_code == 200
    assert response.data == b"<h1>HTML Report</h1>"
