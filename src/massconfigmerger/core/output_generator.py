"""Core component for generating output files."""

import base64
from pathlib import Path
from typing import List

from ..config import Settings
from .format_converters import FormatConverter


class OutputGenerator:
    """Generates subscription and report files from a list of configs."""

    def __init__(self, settings: Settings):
        """
        Initialize the OutputGenerator.

        Args:
            settings: The application settings.
        """
        self.settings = settings

    def write_outputs(
        self, configs: List[str], output_dir: Path
    ) -> List[Path]:
        """
        Write all configured output files.

        Args:
            configs: A list of configuration strings.
            output_dir: The directory to write the files to.

        Returns:
            A list of paths to the written files.
        """
        output_dir.mkdir(exist_ok=True)
        written_files: List[Path] = []

        raw_path = output_dir / "vpn_subscription_raw.txt"
        raw_path.write_text("\n".join(configs), encoding="utf-8")
        written_files.append(raw_path)

        if self.settings.output.write_base64:
            base64_path = output_dir / "vpn_subscription_base64.txt"
            base64_path.write_text(
                base64.b64encode("\n".join(configs).encode()).decode(),
                encoding="utf-8",
            )
            written_files.append(base64_path)

        converter = FormatConverter(configs)

        if self.settings.output.write_clash:
            clash_config_path = output_dir / "clash_config.yaml"
            clash_config_path.write_text(converter.to_clash_config(), encoding="utf-8")
            written_files.append(clash_config_path)

        if self.settings.output.write_clash_proxies:
            clash_proxies_path = output_dir / "clash_proxies.yaml"
            clash_proxies_path.write_text(converter.to_clash_proxies(), encoding="utf-8")
            written_files.append(clash_proxies_path)

        return written_files
