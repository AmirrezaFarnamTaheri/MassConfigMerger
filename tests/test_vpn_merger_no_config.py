import sys
import pytest
from massconfigmerger import vpn_merger


def test_main_missing_config(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "vpn_merger.py",
        "--output-dir",
        str(tmp_path),
    ])
    with pytest.raises(SystemExit) as exc:
        vpn_merger.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "Config file not found" in out
