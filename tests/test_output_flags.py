import os
import sys
import json
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import aggregator_tool


def test_output_files_skip_base64(tmp_path):
    cfg = aggregator_tool.Config(write_base64=False)
    aggregator_tool.output_files(["vmess://a"], tmp_path, cfg)
    assert (tmp_path / "merged.txt").exists()
    assert not (tmp_path / "merged_base64.txt").exists()


def test_output_files_skip_singbox(tmp_path):
    cfg = aggregator_tool.Config(write_singbox=False)
    aggregator_tool.output_files(["vmess://a"], tmp_path, cfg)
    assert (tmp_path / "merged.txt").exists()
    assert not (tmp_path / "merged_singbox.json").exists()


def test_output_files_skip_clash(tmp_path):
    cfg = aggregator_tool.Config(write_clash=False)
    aggregator_tool.output_files(["vmess://a"], tmp_path, cfg)
    assert (tmp_path / "merged.txt").exists()
    assert not (tmp_path / "clash.yaml").exists()


def test_cli_flags_override(monkeypatch, tmp_path):
    cfg_data = {
        "output_dir": str(tmp_path / "out"),
        "log_dir": str(tmp_path / "logs"),
        "write_base64": True,
        "write_singbox": True,
        "write_clash": True,
    }
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg_data))

    recorded = {}

    async def fake_run_pipeline(cfg, *a, **k):
        recorded["cfg"] = cfg
        aggregator_tool.output_files(["vmess://a"], Path(cfg.output_dir), cfg)
        return Path(cfg.output_dir), []

    monkeypatch.setattr(aggregator_tool, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(aggregator_tool, "setup_logging", lambda *_: None)
    monkeypatch.setattr(aggregator_tool, "_get_script_dir", lambda: tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "aggregator_tool.py",
        "--config",
        str(cfg_path),
        "--no-base64",
        "--no-singbox",
        "--no-clash",
    ])

    aggregator_tool.main()

    out_dir = Path(cfg_data["output_dir"])
    assert (out_dir / "merged.txt").exists()
    assert not (out_dir / "merged_base64.txt").exists()
    assert not (out_dir / "merged_singbox.json").exists()
    assert not (out_dir / "clash.yaml").exists()
    cfg = recorded["cfg"]
    assert not cfg.write_base64
    assert not cfg.write_singbox
    assert not cfg.write_clash


def test_cli_no_prune(monkeypatch, tmp_path):
    cfg_path = tmp_path / "c.json"
    cfg_path.write_text(json.dumps({"output_dir": str(tmp_path / "o"), "log_dir": str(tmp_path / "l")}))

    recorded = {}

    async def fake_run_pipeline(cfg, *a, **k):
        recorded.update(k)
        return Path(), []

    monkeypatch.setattr(aggregator_tool, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(aggregator_tool, "setup_logging", lambda *_: None)
    monkeypatch.setattr(aggregator_tool, "_get_script_dir", lambda: tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "aggregator_tool.py",
        "--config",
        str(cfg_path),
        "--no-prune",
    ])

    aggregator_tool.main()

    assert recorded.get("prune") is False


def test_cli_with_merger(monkeypatch, tmp_path):
    cfg_path = tmp_path / "c.json"
    cfg_path.write_text(json.dumps({"output_dir": str(tmp_path / "o"), "log_dir": str(tmp_path / "l")}))

    files = [tmp_path / "o" / "merged.txt", tmp_path / "o" / "merged_base64.txt"]

    async def fake_run_pipeline(*_a, **_k):
        for f in files:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("data")
        return tmp_path / "o", files

    called = {}

    class FakeMerger:
        def __init__(self, path):
            called['arg'] = Path(path)

        async def run(self):
            called['ran'] = True

    monkeypatch.setattr(aggregator_tool, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(aggregator_tool, "setup_logging", lambda *_: None)
    monkeypatch.setattr(aggregator_tool, "_get_script_dir", lambda: tmp_path)
    monkeypatch.setattr(aggregator_tool.vpn_merger, "UltimateVPNMerger", FakeMerger)
    monkeypatch.setattr(sys, "argv", [
        "aggregator_tool.py",
        "--config",
        str(cfg_path),
        "--with-merger",
    ])

    aggregator_tool.main()

    assert called.get('arg') == files[0]
    assert called.get('ran') is True
