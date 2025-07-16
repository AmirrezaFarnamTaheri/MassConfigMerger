import json
import sys
import yaml
from pathlib import Path

from massconfigmerger import aggregator_tool, vpn_merger
from massconfigmerger.config import Settings


def test_output_files_skip_base64(tmp_path):
    cfg = Settings(write_base64=False)
    aggregator_tool.output_files(["vmess://a"], tmp_path, cfg)
    assert (tmp_path / "merged.txt").exists()
    assert not (tmp_path / "merged_base64.txt").exists()


def test_output_files_skip_singbox(tmp_path):
    cfg = Settings(write_singbox=False)
    aggregator_tool.output_files(["vmess://a"], tmp_path, cfg)
    assert (tmp_path / "merged.txt").exists()
    assert not (tmp_path / "merged_singbox.json").exists()


def test_output_files_skip_clash(tmp_path):
    cfg = Settings(write_clash=False)
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
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg_data))

    recorded = {}

    async def fake_run_pipeline(cfg, *a, **k):
        recorded["cfg"] = cfg
        aggregator_tool.output_files(["vmess://a"], Path(cfg.output_dir), cfg)
        return Path(cfg.output_dir), []

    monkeypatch.setattr(aggregator_tool, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(aggregator_tool, "setup_logging", lambda *_: None)
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
    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text(yaml.safe_dump({"output_dir": str(tmp_path / "o"), "log_dir": str(tmp_path / "l")}))

    recorded = {}

    async def fake_run_pipeline(cfg, *a, **k):
        recorded.update(k)
        return Path(), []

    monkeypatch.setattr(aggregator_tool, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(aggregator_tool, "setup_logging", lambda *_: None)
    monkeypatch.setattr(sys, "argv", [
        "aggregator_tool.py",
        "--config",
        str(cfg_path),
        "--no-prune",
    ])

    aggregator_tool.main()

    assert recorded.get("prune") is False


def test_cli_with_merger(monkeypatch, tmp_path):
    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text(yaml.safe_dump({"output_dir": str(tmp_path / "o"), "log_dir": str(tmp_path / "l")}))

    files = [tmp_path / "o" / "merged.txt", tmp_path / "o" / "merged_base64.txt"]

    async def fake_run_pipeline(*_a, **_k):
        for f in files:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("data")
        return tmp_path / "o", files

    called = []

    def fake_detect_and_run(*args):
        called.append(args)

    monkeypatch.setattr(aggregator_tool, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(aggregator_tool, "setup_logging", lambda *_: None)
    monkeypatch.setattr(aggregator_tool.vpn_merger, "detect_and_run", fake_detect_and_run)
    monkeypatch.setattr(sys, "argv", [
        "aggregator_tool.py",
        "--config",
        str(cfg_path),
        "--with-merger",
    ])

    aggregator_tool.main()

    assert called == [tuple()]
    assert aggregator_tool.vpn_merger.CONFIG.resume_file == str(tmp_path / "o" / "merged.txt")


def test_cli_protocols_case_insensitive(monkeypatch, tmp_path):
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(yaml.safe_dump({"output_dir": str(tmp_path / "o"), "log_dir": str(tmp_path / "l")}))

    recorded = {}

    async def fake_run_pipeline(_cfg, protocols, *_a, **_k):
        recorded["protocols"] = protocols
        return tmp_path / "o", []

    monkeypatch.setattr(aggregator_tool, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(aggregator_tool, "setup_logging", lambda *_: None)
    monkeypatch.setattr(sys, "argv", [
        "aggregator_tool.py",
        "--config",
        str(cfg_path),
        "--protocols",
        "VmEsS,TROJAN",
    ])

    aggregator_tool.main()

    assert recorded["protocols"] == ["vmess", "trojan"]


def test_vpn_merger_xyz_flag(monkeypatch, tmp_path):
    def fake_detect_and_run(path=None):
        return None

    monkeypatch.setattr(vpn_merger, "detect_and_run", fake_detect_and_run)
    monkeypatch.setattr(sys, "argv", [
        "vpn_merger.py",
        "--output-dir",
        str(tmp_path),
        "--output-xyz",
        "xyz.conf",
    ])

    vpn_merger.main()

    assert vpn_merger.CONFIG.xyz_file == "xyz.conf"
