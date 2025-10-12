# Configuration

ConfigStream is configured using a `config.yaml` file. This file allows you to customize various aspects of the application. You can use the `config.yaml.example` file as a starting point.

## Telegram

| Setting | Description |
| --- | --- |
| `api_id` | Your Telegram API ID. |
| `api_hash` | Your Telegram API hash. |
| `bot_token` | Your Telegram bot token. |
| `allowed_user_ids` | A list of Telegram user IDs that are allowed to interact with the bot. |
| `session_path` | The path to the Telethon session file. |

## Network

| Setting | Description |
| --- | --- |
| `request_timeout` | The timeout for HTTP requests in seconds. |
| `concurrent_limit` | The maximum number of concurrent HTTP requests. |
| `retry_attempts` | The number of times to retry a failed HTTP request. |
| `retry_base_delay` | The base delay between retries in seconds. |
| `connect_timeout` | The timeout for connection tests in seconds. |
| `http_proxy` | The URL of an HTTP proxy to use for all requests. |
| `socks_proxy` | The URL of a SOCKS proxy to use for all requests. |
| `headers` | A dictionary of HTTP headers to use for all requests. |

## Filtering

| Setting | Description |
| --- | --- |
| `fetch_protocols` | A list of protocols to fetch from sources. |
| `include_patterns` | A list of regex patterns to include configs by their name/remarks. |
| `exclude_patterns` | A list of regex patterns to exclude configs by their name/remarks. |
| `merge_include_protocols` | A list of protocols to include in the final merged output. |
| `merge_exclude_protocols` | A list of protocols to exclude from the final merged output. |
| `include_countries` | A list of country codes to include in the final merged output. |
| `exclude_countries` | A list of country codes to exclude from the final merged output. |
| `max_ping_ms` | The maximum ping in milliseconds to include in the final merged output. |

## Output

| Setting | Description |
| --- | --- |
| `output_dir` | The directory to save output files. |
| `log_dir` | The directory to save log files. |
| `history_db_file` | The path to the proxy history database file. |
| `write_base64` | Whether to write a base64-encoded subscription file. |
| `write_singbox` | Whether to write a Sing-box configuration file. |
| `write_clash` | Whether to write a Clash configuration file. |
| `write_csv` | Whether to write a CSV report. |
| `write_html` | Whether to write an HTML report. |
| `write_clash_proxies` | Whether to write a minimal Clash YAML file with only the proxies. |
| `surge_file` | The path to a Surge configuration file to write. |
| `qx_file` | The path to a Quantumult X configuration file to write. |
| `github_token` | A GitHub personal access token to use for uploading files to a Gist. |

## Processing

| Setting | Description |
| --- | --- |
| `sort_by` | The field to sort the final merged output by. Can be `latency` or `reliability`. |
| `enable_sorting` | Whether to sort the final merged output. |
| `enable_url_testing` | Whether to perform connection tests. |
| `top_n` | The number of top configs to keep in the final merged output. `0` to keep all. |
| `shuffle_sources` | Whether to process sources in a random order. |
| `max_configs_per_source` | The maximum number of configs to process from each source. |
| `geoip_db` | The path to a GeoIP database file. |
| `resume_file` | The path to a previous output file to resume from. |
| `max_retries` | The number of times to retry a failed connection test. |

## Security

| Setting | Description |
| --- | --- |
| `apivoid_api_key` | An API key for the APIVoid IP Reputation API. |
| `blocklist_detection_threshold` | The number of blacklist detections required to consider an IP malicious. `0` to disable. |
| `web_api_token` | A token required by the web dashboard for running aggregation/merge actions. |