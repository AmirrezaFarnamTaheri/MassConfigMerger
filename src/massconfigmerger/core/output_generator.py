"""Core components for generating output files."""

import base64
import json
from pathlib import Path
from typing import Any, Dict, List

from .. import clash_utils
from ..advanced_converters import generate_qx_conf, generate_surge_conf
from ..config import Settings


class OutputGenerator:
    """Generates various output files from a list of configurations."""

    def __init__(self, settings: Settings):
        """
        Initialize the OutputGenerator.

        Args:
            settings: The application settings.
        """
        self.settings = settings

    def write_outputs(self, configs: List[str], output_dir: Path) -> List[Path]:
        """
        Write the configurations to the specified output directory.

        Args:
            configs: A list of configuration links.
            output_dir: The directory to write the output files to.

        Returns:
            A list of paths to the generated files.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        written_files: List[Path] = []

        # Write raw configs
        raw_path = output_dir / "vpn_subscription_raw.txt"
        raw_path.write_text("\n".join(configs), encoding="utf-8")
        written_files.append(raw_path)

        # Write base64 encoded configs
        if self.settings.write_base64:
            base64_path = output_dir / "vpn_subscription_base64.txt"
            base64_content = base64.b64encode("\n".join(configs).encode()).decode()
            base64_path.write_text(base64_content, encoding="utf-8")
            written_files.append(base64_path)

        # Write Clash config
        if self.settings.write_clash:
            proxies = self._generate_clash_proxies(configs)
            if proxies:
                clash_yaml = clash_utils.build_clash_config(proxies)
                clash_file = output_dir / "clash.yaml"
                clash_file.write_text(clash_yaml, encoding="utf-8")
                written_files.append(clash_file)

        # Write Surge config
        if self.settings.surge_file:
            proxies = self._generate_clash_proxies(configs)
            if proxies:
                surge_content = generate_surge_conf(proxies)
                surge_path = output_dir / self.settings.surge_file
                surge_path.write_text(surge_content, encoding="utf-8")
                written_files.append(surge_path)

        # Write Quantumult X config
        if self.settings.qx_file:
            proxies = self._generate_clash_proxies(configs)
            if proxies:
                qx_content = generate_qx_conf(proxies)
                qx_path = output_dir / self.settings.qx_file
                qx_path.write_text(qx_content, encoding="utf-8")
                written_files.append(qx_path)

        return written_files

    def _generate_clash_proxies(self, configs: List[str]) -> List[Dict[str, Any]]:
        """Generate a list of Clash proxies from the configurations."""
        proxies = []
        for i, link in enumerate(configs):
            proxy = clash_utils.config_to_clash_proxy(link, i)
            if proxy:
                proxies.append(proxy)
        return proxies