import sys
from pathlib import Path
from massconfigmerger import vpn_merger
from massconfigmerger.result_processor import CONFIG
from massconfigmerger.config import Settings


def test_cli_country_flags(monkeypatch, tmp_path):
    recorded = {}

    def fake_detect_and_run(path=None):
        recorded['include'] = CONFIG.include_countries
        recorded['exclude'] = CONFIG.exclude_countries
        return None

    monkeypatch.setattr(vpn_merger, "detect_and_run", fake_detect_and_run)
    monkeypatch.setattr(vpn_merger, "load_config", lambda: Settings())
    monkeypatch.setattr(CONFIG, "include_countries", None)
    monkeypatch.setattr(CONFIG, "exclude_countries", None)
    monkeypatch.setattr(sys, "argv", [
        "vpn_merger.py",
        "--output-dir", str(tmp_path),
        "--include-country", "US,CA",
        "--exclude-country", "CN",
    ])

    vpn_merger.main()

    assert recorded['include'] == {"US", "CA"}
    assert recorded['exclude'] == {"CN"}
