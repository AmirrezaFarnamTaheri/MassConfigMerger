# Mass Config Merger 🚀

Automated toolchain for collecting, testing and merging free VPN configuration
links from hundreds of public sources.

[![CI](https://github.com/AmirrezaFarnamTaheri/MassConfigMerger/actions/workflows/ci.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/MassConfigMerger/actions/workflows/ci.yml)
[](https://opensource.org/licenses/MIT)

Welcome to **Mass Config Merger**! This project provides a powerful Python script that automatically fetches VPN configurations from the over 470 public sources listed in `sources.txt`, tests their connectivity, and merges them into a single, performance-sorted subscription link for use in your favorite VPN client. It can even save incremental batches while running so you always have up-to-date results.
Both `aggregator_tool.py` and `vpn_merger.py` read from this same `sources.txt` file, so updating the list once applies to all tools.

```mermaid
flowchart LR
    S[Sources] --> A[aggregator\_tool]
    A --> M[vpn\_merger]
    M --> O[Output Files]
```

This guide is designed for **everyone**, from absolute beginners with no coding experience to advanced users who want full automation.

> **Note**: The default protocol list is optimised for the Hiddify client. Other VPN apps may require adjusting `--include-protocols`.

**Important**: Install the dependencies with `pip install -r requirements.txt` before running **any** of the Python scripts.

### ⚡ Quick Start

1. **Install Python 3.8 or newer**
   - On **Windows** download it from [python.org](https://www.python.org/downloads/) and tick *Add Python to PATH* during setup.
   - On **macOS/Linux** use your package manager, e.g. `sudo apt install python3`.

2. **Clone the repository**

   ```bash
   git clone https://github.com/AmirrezaFarnamTaheri/MassConfigMerger.git
   cd MassConfigMerger
   ```

3. **Install the requirements**

   ```bash
   pip install -r requirements.txt
   ```

   *Install `geoip2` as well if you plan to filter by country and download the free GeoLite2 database from MaxMind.*

4. **Gather configuration links**

   ```bash
   python aggregator_tool.py --hours 12
   ```

   This creates `output/merged.txt` and a log file under `logs/` named by the current date.

5. **Merge and sort the results**

   ```bash
   python vpn_merger.py
   ```

   Use `--resume output/merged.txt` to continue a previous run without re-downloading.

6. **All in one step**

   ```bash
   python aggregator_tool.py --with-merger
   ```

   The merger automatically runs on the freshly aggregated results using the
   resume feature.

7. **Country filters**

   ```bash
   python vpn_merger.py --geoip-db GeoLite2-Country.mmdb --include-country US,CA
   ```

   Combine `--include-country` or `--exclude-country` with `--geoip-db` to select preferred regions.

8. **Check the logs**

   Every run writes detailed output to `logs/YYYY-MM-DD.log`. Review these files with `less` or `tail -f` to monitor progress and diagnose issues.

9. **Import your subscription**
   - Use the link in `output/vpn_subscription_base64.txt` (unless `--no-base64` was used) or load `vpn_singbox.json` in clients like sing-box.


## 📖 Table of Contents

- [Quick Start](#-quick-start)
- [Full Tutorial](docs/tutorial.md)
- [Protocol Deep Dive](docs/protocol-deep-dive.md)
- [Advanced Troubleshooting](docs/advanced-troubleshooting.md)
- [📂 Understanding the Output Files](#-understanding-the-output-files)
- [FAQ](#faq)


## 📂 Understanding the Output Files

| File Name                              | Purpose                                                                                                  |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `vpn_subscription_base64.txt` | *(optional)* A base64-encoded file. Most apps import directly from this file's raw URL.                  |
| `vpn_subscription_raw.txt`    | A plain text list of all the VPN configuration links.                                                    |
| `vpn_detailed.csv`            | *(optional)* A spreadsheet with detailed info about each server, including protocol, host, and ping time. |
| `vpn_report.json`             | A detailed report with all stats and configurations in a developer-friendly format.                      |
| `vpn_singbox.json`            | Outbound objects ready for import into sing-box/Stash.                                                   |
| `clash.yaml`                  | Clash configuration with all proxies and a basic group. Compatible with Clash/Clash Meta.                  |
| `vpn_clash_proxies.yaml`      | Minimal Clash YAML listing only the proxies, suitable as a provider.                                      |

### Important Notes

- The script only runs when executed and does **not** stay running in the
  background.  Use your operating system's scheduler if you need periodic
  updates.
- When scraping Telegram make sure you only access **public** channels and
  respect Telegram's Terms of Service along with your local laws.
- All events are logged to the directory specified in `log_dir` (defaults to
  `logs/` here) so you can audit what was fetched and from where.

### Docker Compose Automation

The included `docker-compose.yml` automates running the scripts. `vpn_merger`
loops every `MERGE_INTERVAL` seconds (default `86400`). Enable the optional
`aggregator` profile to fetch new links on a schedule. It runs
`aggregator_tool.py --with-merger` every `AGGREGATE_INTERVAL` seconds
(default `43200`). The `retester` profile repeatedly runs
`vpn_retester.py` in the same way.

Start all services with:

```bash
docker compose up -d
```

Add profiles as needed, for example:

```bash
docker compose --profile aggregator --profile retester up -d
```

Key environment variables used by the compose file:

- `MERGE_INTERVAL` – seconds between each run of `vpn_merger` (default `86400`)
- `AGGREGATE_INTERVAL` – seconds between aggregator runs when the `aggregator` profile is enabled (default `43200`)

## FAQ

### Why does the script take so long?
The merger checks hundreds of servers. Reduce the number of sources or use a smaller `--concurrent-limit`. Skipping tests with `--no-url-test` can also speed up runs.

### There is no output directory
Ensure you ran the script in this repository and watch for errors. Results are saved in the `output/` folder or the location given by `--output-dir`.

### Telegram authentication errors
Verify your `telegram_api_id`, `telegram_api_hash` and bot token. Incorrect credentials or using a restricted account will prevent the aggregator from accessing Telegram.

### GeoIP lookup errors
Install the `geoip2` package and download the free GeoLite2 database from MaxMind. Pass `--geoip-db /path/to/GeoLite2-Country.mmdb` to enable country filtering.


## Testing

Run `pytest` to execute the test suite. Make sure to install both the runtime
and development dependencies first:

```bash
pip install -r requirements.txt -r dev-requirements.txt
pip install -e .  # or export PYTHONPATH=$PWD
```


## Changelog & Contributing

See [CHANGELOG.md](CHANGELOG.md) for a summary of new features and updates.
If you encounter problems or have improvements, please open an issue or submit a pull request on [GitHub](https://github.com/AmirrezaFarnamTaheri/MassConfigMerger).
Contributors can also install packages from `dev-requirements.txt`.
