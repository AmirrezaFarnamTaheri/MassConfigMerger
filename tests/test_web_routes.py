from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest

from massconfigmerger.web import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
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
    fs.create_file("config.yaml", contents="output:\n  output_dir: 'fake_output'")
    fs.create_file("fake_output/vpn_subscription_raw.txt")

    response = client.get("/merge")

    assert response.status_code == 200
    assert response.json == {"status": "merge complete"}
    mock_run_merger.assert_awaited_once()


def test_merge_route_no_resume_file(client, fs):
    """Test the /merge route when the resume file is missing."""
    fs.create_file("config.yaml", contents="output:\n  output_dir: 'fake_output'")

    response = client.get("/merge")

    assert response.status_code == 404
    assert "error" in response.json


def test_report_route_html(client, fs):
    """Test the /report route when an HTML report exists."""
    fs.create_file("config.yaml", contents="output:\n  output_dir: '/app/fake_output'")
    fs.create_file("/app/fake_output/vpn_report.html", contents=b"<h1>HTML Report</h1>")

    response = client.get("/report")

    assert response.status_code == 200
    assert response.data == b"<h1>HTML Report</h1>"


def test_report_route_json(client, fs):
    """Test the /report route when only a JSON report exists."""
    fs.create_file("config.yaml", contents="output:\n  output_dir: '/app/fake_output'")
    fs.create_file("/app/fake_output/vpn_report.json", contents='{"key": "value"}')

    response = client.get("/report")

    assert response.status_code == 200
    assert "<h1>VPN Report</h1>" in response.data.decode()
    assert '&#34;key&#34;: &#34;value&#34;' in response.data.decode()


def test_report_route_not_found(client, fs):
    """Test the /report route when no report is found."""
    fs.create_file("config.yaml", contents="output:\n  output_dir: '/app/fake_output'")

    response = client.get("/report")

    assert response.status_code == 404
    assert b"Report not found" in response.data


@patch("massconfigmerger.web.app.run")
def test_main_run(mock_run):
    """Test that the main function calls app.run."""
    from massconfigmerger.web import main
    main()
    mock_run.assert_called_once_with(host="0.0.0.0", port=8080)