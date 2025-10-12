from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

def test_api_status(client):
    """Test the /api/status endpoint."""
    with patch("psutil.cpu_percent", return_value=50.0), \
         patch("psutil.virtual_memory") as mock_mem:

        mock_mem.return_value.total = 4 * 1024 * 1024 * 1024
        mock_mem.return_value.used = 1 * 1024 * 1024 * 1024
        mock_mem.return_value.percent = 25.0

        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.get_json()
        assert "uptime" in data
        assert data["cpu"]["percent"] == 50.0
        assert data["memory"]["percent"] == 25.0

def test_api_logs(client, fs):
    """Test the /api/logs endpoint."""
    log_content = "line 1\nline 2\n"
    fs.create_file("configstream.log", contents=log_content)

    response = client.get("/api/logs")
    assert response.status_code == 200
    data = response.get_json()
    assert data["logs"] == ["line 1", "line 2"]

def test_api_logs_file_not_found(client, fs):
    """Test the /api/logs endpoint when the log file does not exist."""
    response = client.get("/api/logs")
    assert response.status_code == 200
    data = response.get_json()
    assert data["logs"] == ["Log file not found."]