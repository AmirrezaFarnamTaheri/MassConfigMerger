from __future__ import annotations

import os
from pathlib import Path


def generate_files(results: list[tuple[str, bool]], output_dir: str):
    """
    Generates output files from the test results.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Base64 file
    with open(output_path / "base64.txt", "w") as f:
        for config, working in results:
            if working:
                # This is a placeholder. In a real scenario, you would
                # properly encode the config to base64.
                f.write(config + "\n")

    # Clash file
    with open(output_path / "clash.yaml", "w") as f:
        f.write("proxies:\n")
        for config, working in results:
            if working:
                # This is a placeholder. In a real scenario, you would
                # convert the config to a Clash proxy entry.
                f.write(f"- name: {config}\n")
                f.write("  type: vmess\n")
                f.write("  server: server_address\n")
                f.write("  port: 12345\n")
                f.write("  uuid: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\n")
                f.write("  alterId: 0\n")
                f.write("  cipher: auto\n")

    # Report file
    with open(output_path / "report.csv", "w") as f:
        f.write("config,working\n")
        for config, working in results:
            f.write(f"{config},{working}\n")