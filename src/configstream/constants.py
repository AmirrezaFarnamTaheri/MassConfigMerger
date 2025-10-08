from pathlib import Path
import re

SOURCES_FILE = Path("sources.txt")
CHANNELS_FILE = Path("channels.txt")

# Regular expressions shared across modules
PROTOCOL_RE = re.compile(
    r"\b(?:"
    r"vmess|vless|reality|ssr?|trojan|hy2|hysteria2?|tuic|"
    r"shadowtls|juicity|naive|brook|wireguard|"
    r"socks5|socks4|socks|https|http"
    r")://[^\s\"'<>()\[\]{}]+",
    re.IGNORECASE,
)
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=_-]+$")

# Safety limit for base64 decoding to avoid huge payloads
MAX_DECODE_SIZE = 256 * 1024  # 256 kB

# Default file names
CONFIG_FILE_NAME = "config.yaml"
SOURCES_FAILURES_FILE_SUFFIX = ".failures.json"
SOURCES_DISABLED_FILE_NAME = "sources_disabled.txt"
RAW_SUBSCRIPTION_FILE_NAME = "vpn_subscription_raw.txt"
BASE64_SUBSCRIPTION_FILE_NAME = "vpn_subscription_base64.txt"
CLASH_PROXIES_FILE_NAME = "vpn_clash_proxies.yaml"
CLASH_CONFIG_FILE_NAME = "clash.yaml"
JSON_REPORT_FILE_NAME = "vpn_report.json"
HTML_REPORT_FILE_NAME = "vpn_report.html"
CSV_REPORT_FILE_NAME = "vpn_detailed.csv"
RETESTED_RAW_FILE_NAME = "vpn_retested_raw.txt"
RETESTED_BASE64_FILE_NAME = "vpn_retested_base64.txt"
RETESTED_CSV_FILE_NAME = "vpn_retested_detailed.csv"
UPLOAD_LINKS_FILE_NAME = "upload_links.txt"
HISTORY_DB_FILE_NAME = "proxy_history.db"
