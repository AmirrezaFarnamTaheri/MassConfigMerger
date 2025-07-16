import json
import sys
import yaml
from pathlib import Path

from massconfigmerger import aggregator_tool
from massconfigmerger.config import Settings


def test_output_files_skip_base64(tmp_path):
    cfg = Settings(write_base64=False)
    aggregator_tool.output_files(["vmess://a"], tmp_path, cfg)
    assert (tmp_path / "vpn_subscription_raw.txt").exists()
    assert not (tmp_path / "vpn_subscription_base64.txt").exists()


def test_output_files_skip_singbox(tmp_path):
    cfg = Settings(write_singbox=False)
    aggregator_tool.output_files(["vmess://a"], tmp_path, cfg)
    assert (tmp_path / "vpn_subscription_raw.txt").exists()
    assert not (tmp_path / "vpn_singbox.json").exists()


def test_output_files_skip_clash(tmp_path):
    cfg = Settings(write_clash=False)
    aggregator_tool.output_files(["vmess://a"], tmp_path, cfg)
    assert (tmp_path / "vpn_subscription_raw.txt").exists()
    assert not (tmp_path / "clash.yaml").exists()


def test_output_files_extra_formats(tmp_path):
    cfg = Settings(surge_file="s.conf", qx_file="q.conf", xyz_file="x.conf")
    aggregator_tool.output_files(["vmess://a"], tmp_path, cfg)
    assert (tmp_path / "s.conf").exists()
    assert (tmp_path / "q.conf").exists()
    assert (tmp_path / "x.conf").exists()


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
    assert (out_dir / "vpn_subscription_raw.txt").exists()
    assert not (out_dir / "vpn_subscription_base64.txt").exists()
    assert not (out_dir / "vpn_singbox.json").exists()
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

    files = [
        tmp_path / "o" / "vpn_subscription_raw.txt",
        tmp_path / "o" / "vpn_subscription_base64.txt",
    ]

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
    assert (
        aggregator_tool.vpn_merger.CONFIG.resume_file
        == str(tmp_path / "o" / "vpn_subscription_raw.txt")
    )



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


def test_cli_output_format_flags(monkeypatch, tmp_path):
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        yaml.safe_dump({"output_dir": str(tmp_path / "o"), "log_dir": str(tmp_path / "l")})
    )

    async def fake_run_pipeline(cfg, *a, **k):
        aggregator_tool.output_files(["vmess://a"], Path(cfg.output_dir), cfg)
        return Path(cfg.output_dir), []

    monkeypatch.setattr(aggregator_tool, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(aggregator_tool, "setup_logging", lambda *_: None)
    monkeypatch.setattr(sys, "argv", [
        "aggregator_tool.py",
        "--config",
        str(cfg_path),
        "--output-surge",
        "s.conf",
        "--output-qx",
        "q.conf",
        "--output-xyz",
        "x.conf",
    ])

    aggregator_tool.main()

    out_dir = tmp_path / "o"
    assert (out_dir / "s.conf").exists()
    assert (out_dir / "q.conf").exists()
    assert (out_dir / "x.conf").exists()
