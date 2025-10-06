from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest

from massconfigmerger.web import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from prometheus_client import make_wsgi_app
    app.config["TESTING"] = True
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})
    with app.test_client() as client:
        yield client


@patch("massconfigmerger.web.run_aggregation_pipeline", new_callable=AsyncMock)
@patch("massconfigmerger.web.load_config")
def test_aggregate_route(mock_load_config, mock_run_pipeline, client, fs):
    """Test the /aggregate route."""
    fs.create_file("config.yaml")
    mock_run_pipeline.return_value = (Path("/fake/dir"), [Path("/fake/dir/file.txt")])

    response = client.get("/aggregate")

    assert response.status_code == 200
    assert response.json == {
        "output_dir": "/fake/dir",
        "files": ["/fake/dir/file.txt"],
    }
    mock_run_pipeline.assert_awaited_once()


@patch("massconfigmerger.web.run_merger_pipeline", new_callable=AsyncMock)
def test_merge_route_success(mock_run_merger, client, fs):
    """Test the /merge route when the resume file exists."""
    fs.create_file("pyproject.toml")
    fs.create_file("config.yaml", contents="output:\n  output_dir: 'fake_output'")
    fs.create_dir("fake_output")
    fs.create_file("fake_output/vpn_subscription_raw.txt")

    response = client.get("/merge")

    assert response.status_code == 200
    assert response.json == {"status": "merge complete"}
    mock_run_merger.assert_awaited_once()


def test_merge_route_no_resume_file(client, fs):
    """Test the /merge route when the resume file is missing."""
    fs.create_file("pyproject.toml")
    fs.create_file("config.yaml", contents="output:\n  output_dir: 'fake_output'")
    fs.create_dir("fake_output")

    response = client.get("/merge")

    assert response.status_code == 404
    assert "error" in response.json


def test_report_route_html(client, fs):
    """Test the /report route when an HTML report exists."""
    fs.create_file("pyproject.toml")
    fs.create_file("config.yaml", contents="output:\n  output_dir: 'fake_output'")
    fs.create_dir("fake_output")
    fs.create_file("fake_output/vpn_report.html", contents=b"<h1>HTML Report</h1>")

    response = client.get("/report")

    assert response.status_code == 200
    assert response.data == b"<h1>HTML Report</h1>"


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


@patch("massconfigmerger.web.app.run")
def test_main_run(mock_run):
    """Test that the main function calls app.run."""
    from massconfigmerger.web import main
    main()
    mock_run.assert_called_once_with(host="0.0.0.0", port=8080)


def test_index_route(client):
    """Test the index route."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"MassConfigMerger Dashboard" in response.data


def test_health_check_route(client):
    """Test the /health route."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


@patch("massconfigmerger.web.Database")
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

    # Check that the data is sorted by reliability
    p1 = data.find("proxy1")
    p2 = data.find("proxy2")
    p3 = data.find("proxy3")
    p4 = data.find("proxy4")
    assert -1 < p1 < p4 < p2 < p3

    # Check for correct data rendering
    assert "100.00%" in data
    assert '2023-01-01 00:00:00' in data
    assert "50.00%" in data
    assert "0.00%" in data
    assert "N/A" in data

    mock_db_instance.connect.assert_awaited_once()
    mock_db_instance.get_proxy_history.assert_awaited_once()
    mock_db_instance.close.assert_awaited_once()


@patch("massconfigmerger.web.Database")
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
    assert response.data.count(b"<tr>") == 1


@patch("massconfigmerger.web.Database")
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


def test_metrics_route(client):
    """Test the /metrics route."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"python_info" in response.data


@patch("massconfigmerger.web.run_aggregation_pipeline", new_callable=AsyncMock)
@patch("massconfigmerger.web.load_config")
def test_aggregate_route_exception(mock_load_config, mock_run_pipeline, client, fs):
    """Test the /aggregate route when an exception occurs."""
    fs.create_file("config.yaml")
    mock_run_pipeline.side_effect = Exception("Test exception")

    with pytest.raises(Exception, match="Test exception"):
        client.get("/aggregate")