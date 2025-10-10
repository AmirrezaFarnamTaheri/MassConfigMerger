# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

"""Protocol-specific parsers for VPN configuration links.

This package contains individual modules for parsing various VPN protocols
(e.g., VMess, VLESS, Trojan) from their configuration links into a
standardized dictionary format that can be used by other components of the
application, such as the Clash configuration generator.

Each module is expected to provide a `parse` function that takes the
configuration string and returns a dictionary of its components or `None`
if parsing fails. This modular approach allows for easy extension to support
new protocols.
"""
from __future__ import annotations
