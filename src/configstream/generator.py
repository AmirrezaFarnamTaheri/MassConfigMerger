from __future__ import annotations

from pathlib import Path

from .core import (
    Proxy,
    generate_base64_subscription,
    generate_clash_config,
    generate_raw_configs,
)


def generate_files(proxies: list[Proxy], output_dir: str):
    """
    Generates all output files from the tested proxies.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate Base64 subscription file
    base64_content = generate_base64_subscription(proxies)
    if base64_content:
        (output_path / "vpn_subscription_base64.txt").write_text(
            base64_content, encoding="utf-8"
        )

    # Generate Clash configuration file
    clash_content = generate_clash_config(proxies)
    if clash_content:
        (output_path / "clash.yaml").write_text(clash_content, encoding="utf-8")

    # Generate raw configs file
    raw_content = generate_raw_configs(proxies)
    if raw_content:
        (output_path / "configs_raw.txt").write_text(raw_content, encoding="utf-8")

    # Generate a simple report
    report_content = ["config,is_working,latency_ms"]
    for p in proxies:
        report_content.append(f"{p.config},{p.is_working},{p.latency or ''}")
    (output_path / "report.csv").write_text(
        "\n".join(report_content), encoding="utf-8"
    )