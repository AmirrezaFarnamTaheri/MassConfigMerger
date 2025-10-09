from __future__ import annotations

import json
from pathlib import Path

import pytest

from configstream.config import Settings
from configstream.core.config_processor import ConfigResult
from configstream.report_generator import (
    generate_html_report,
    generate_json_report,
)


@pytest.fixture
def sample_results() -> list[ConfigResult]:
    """Return a sample list of ConfigResult objects for testing."""
    return [
        ConfigResult(
            config="vmess://config1",
            protocol="VMess",
            host="example.com",
            port=443,
            ping_time=0.123,
            is_reachable=True,
            source_url="http://source.com",
            country="US",
        )
    ]


def test_generate_json_report(fs, sample_results: list[ConfigResult]):
    """Test the generation of a JSON report."""
    fs.create_dir("/output")
    output_dir = Path("/output")
    settings = Settings()
    stats = {"total": 1}
    start_time = 0

    report_path = generate_json_report(
        sample_results, stats, output_dir, start_time, settings
    )

    assert report_path.exists()
    report_data = json.loads(report_path.read_text())

    assert report_data["statistics"]["total"] == 1
    assert len(report_data["results"]) == 1
    assert report_data["results"][0]["host"] == "example.com"
    assert report_data["results"][0]["ping_ms"] == 123.0


def test_generate_html_report(fs, sample_results: list[ConfigResult]):
    """Test the generation of an HTML report."""
    fs.create_dir("/output")
    output_dir = Path("/output")

    report_path = generate_html_report(sample_results, output_dir)

    assert report_path.exists()
    html_content = report_path.read_text()

    assert "<td>VMess</td>" in html_content
    assert "<td>example.com</td>" in html_content
    assert "<td>123.0</td>" in html_content
    assert "<td>US</td>" in html_content
