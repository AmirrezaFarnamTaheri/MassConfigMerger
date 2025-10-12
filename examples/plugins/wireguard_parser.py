"""Example plugin: WireGuard configuration parser."""
from configstream.plugins.base import ParserPlugin, PluginMetadata, OutputPlugin


class WireGuardParser(ParserPlugin):
    """Parser for WireGuard configuration format.

    Handles wireguard:// URLs and extracts connection details.
    """

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="wireguard-parser",
            version="1.0.0",
            author="ConfigStream Team",
            description="Parses WireGuard configuration URLs",
            priority=50
        )

    def can_parse(self, config: str) -> bool:
        """Check if config is WireGuard format."""
        return config.startswith("wireguard://")

    def parse(self, config: str) -> dict:
        """Parse WireGuard config.

        Format: wireguard://publickey@host:port?privatekey=XXX
        """
        # Remove protocol
        config = config.replace("wireguard://", "")

        # Split into parts
        if "@" not in config:
            raise ValueError("Invalid WireGuard config format")

        public_key, rest = config.split("@", 1)

        # Extract host and port
        if ":" not in rest:
            raise ValueError("Port not specified")

        host_port, params = rest.split("?", 1) if "?" in rest else (rest, "")
        host, port = host_port.rsplit(":", 1)

        # Parse parameters
        param_dict = {}
        if params:
            for param in params.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    param_dict[key] = value

        return {
            "protocol": "wireguard",
            "host": host,
            "port": int(port),
            "public_key": public_key,
            "private_key": param_dict.get("privatekey", ""),
            "allowed_ips": param_dict.get("allowed_ips", "0.0.0.0/0")
        }


class TomlOutputPlugin(OutputPlugin):
    """Output plugin for TOML format."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="toml",
            version="1.0.0",
            author="ConfigStream Team",
            description="Outputs configurations in TOML format"
        )

    @property
    def file_extension(self) -> str:
        return ".toml"

    def format(self, nodes: list) -> str:
        """Format nodes as TOML."""
        lines = ["# ConfigStream Output", ""]

        for i, node in enumerate(nodes):
            lines.append("[[nodes]]")
            lines.append(f'protocol = "{node.get("protocol")}"')
            lines.append(f'ip = "{node.get("ip")}"')
            lines.append(f'port = {node.get("port")}')
            lines.append(f'ping_ms = {node.get("ping_ms")}')
            lines.append(f'country = "{node.get("country", "Unknown")}"')
            lines.append("")

        return "\n".join(lines)
