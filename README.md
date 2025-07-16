# Mass Config Merger 🚀

Automated toolchain for collecting, testing and merging free VPN configuration
links from hundreds of public sources.

[![CI](https://github.com/AmirrezaFarnamTaheri/MassConfigMerger/actions/workflows/ci.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/MassConfigMerger/actions/workflows/ci.yml)
[](https://opensource.org/licenses/MIT)

Welcome to **Mass Config Merger**! This project provides a powerful Python script that automatically fetches VPN configurations from the over 470 public sources listed in `sources.txt`, tests their connectivity, and merges them into a single, performance-sorted subscription link for use in your favorite VPN client. It can even save incremental batches while running so you always have up-to-date results.
Both `aggregator_tool.py` and `vpn_merger.py` read from this same `sources.txt` file, so updating the list once applies to all tools. After installing the package with `pip install -e .` (or `pip install massconfigmerger` from PyPI) you can invoke them as `aggregator-tool`, `vpn-merger`, `vpn-retester` and `massconfigmerger`.

```mermaid
flowchart LR
    S[Sources] --> A[aggregator\_tool]
    A --> M[vpn\_merger]
    M --> O[Output Files]
```

This guide is designed for **everyone**, from absolute beginners with no coding experience to advanced users who want full automation.

**Security Note**: All VPN servers collected by this tool are pulled from public sources. Because the server owners are unknown, treat them as untrusted and avoid using them for banking or other sensitive activities. See the [full disclaimer](docs/tutorial.md#-important-security--privacy-disclaimer) for more details.

> **Note**: The default protocol list is optimised for the Hiddify client. Other VPN apps may require adjusting `--include-protocols`.

> **How protocols are filtered**
>
> The `protocols` list in the **Aggregator options** section of
> [`config.yaml.example`](config.yaml.example) controls which types of links are
> collected from each source. Reduce this list if you only want certain
> protocols to speed up scraping.
>
> Later the merger applies its own `include_protocols` list (see the **Merger
> options** in `config.yaml.example`) to drop any unwanted protocols before
> writing the final files. Adjust this list to match what your VPN client
> supports or to exclude protocols you don't trust.

**Important**: Install the dependencies with `pip install -r requirements.txt` before running **any** of the Python scripts. You can also run `pip install -e .` (or install from PyPI) to register the `aggregator-tool`, `vpn-merger` and `vpn-retester` commands.

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
   # optional: install the package so the CLI tools are on your PATH
   pip install -e .
   # for development (tests, linters)
   pip install -e .[dev]
   ```

   *Install `geoip2` as well if you plan to filter by country and download the free GeoLite2 database from MaxMind.*

4. **Gather configuration links**

   ```bash
   python aggregator_tool.py --hours 12
   # or
   aggregator-tool --hours 12
   # or
   massconfigmerger fetch --hours 12
   ```

   `aggregator_tool.py` on its own creates `output/merged.txt` (plus `merged_base64.txt` and `merged_singbox.json`) and a log file under `logs/` named by the current date.

5. **Merge and sort the results**

   ```bash
   python vpn_merger.py
   # or
   vpn-merger
   # or
   massconfigmerger merge
   ```

   Use `--resume output/merged.txt` to continue a previous run without re-downloading.

6. **All in one step**

   ```bash
   python aggregator_tool.py --with-merger
   # or
   aggregator-tool --with-merger
   # or
   massconfigmerger full
   ```

   The merger automatically runs on the freshly aggregated results using the
   resume feature.

7. **Country filters**

   ```bash
   python vpn_merger.py --geoip-db GeoLite2-Country.mmdb --include-country US,CA
   # or
   vpn-merger --geoip-db GeoLite2-Country.mmdb --include-country US,CA
   ```

   Combine `--include-country` or `--exclude-country` with `--geoip-db` to select preferred regions.

8. **Check the logs**

   Every run writes detailed output to `logs/YYYY-MM-DD.log`. Review these files with `less` or `tail -f` to monitor progress and diagnose issues.

9. **Import your subscription**
   - Use the link in `output/vpn_subscription_base64.txt` (unless `--no-base64` was used) or load `vpn_singbox.json` in clients like sing-box.

> **Need more options?** Run `vpn-merger --help-extra` or see
> [docs/tutorial.md](docs/tutorial.md) for the full walkthrough.


## 📖 Table of Contents

- [Quick Start](#-quick-start)
- [Full Tutorial](docs/tutorial.md)
- [Protocol Deep Dive](docs/protocol-deep-dive.md)
- [Advanced Troubleshooting](docs/advanced-troubleshooting.md)
- [📂 Understanding the Output Files](#-understanding-the-output-files)
- [Advanced Features](#advanced-features)
- [FAQ](#faq)


## 📂 Understanding the Output Files

| File Name                              | Purpose                                                                                                  |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `merged.txt` | Raw links collected from all sources. |
| `merged_base64.txt` | Base64-encoded version of `merged.txt`. |
| `merged_singbox.json` | Basic sing-box JSON from the aggregator. |
| `vpn_subscription_base64.txt` | *(optional)* A base64-encoded file. Most apps import directly from this file's raw URL.                  |
| `vpn_subscription_raw.txt`    | A plain text list of all the VPN configuration links.                                                    |
| `vpn_detailed.csv`            | *(optional)* A spreadsheet with detailed info about each server, including protocol, host, and ping time. |
| `vpn_report.json`             | A detailed report with all stats and configurations in a developer-friendly format.                      |
| `vpn_singbox.json`            | Outbound objects ready for import into sing-box/Stash.                                                   |
| `clash.yaml`                  | Clash configuration with all proxies and a basic group. Compatible with Clash/Clash Meta.                  |
| `vpn_clash_proxies.yaml`      | Minimal Clash YAML listing only the proxies, suitable as a provider.                                      |
| `surge.conf` *(via `--output-surge`)* | Surge format configuration. Works with Surge iOS/macOS 5 or later.                                    |
| `quantumultx.conf` *(via `--output-qx`)* | Quantumult X server list compatible with version 1.1.9+ on iOS.                                      |
| `xyz.conf` *(via `--output-xyz`)* | Demonstration XYZ format listing basic proxy info. |

All of these files are written to the directory specified by `--output-dir`
(defaults to `output/`) unless an absolute path is given.

### Surge & Quantumult X Usage

Generate client-specific output automatically:

```bash
python vpn_merger.py --output-surge surge.conf --output-qx quantumultx.conf --output-xyz xyz.conf
```

Once the files are generated, host them somewhere your phone can reach or copy
them directly to the device. In Surge, open **Settings → Configuration →
Download** and provide the URL to `surge.conf`. For Quantumult X, go to
**Settings → Server List → Import** and select the `quantumultx.conf` file or a
remote URL. Refer to the [Surge manual](https://manual.nssurge.com/) and the
[Quantumult X examples](https://github.com/KOP-XIAO/QuantumultX) for details.

Example of generating and serving the files locally:

```bash
python vpn_merger.py --output-surge surge.conf --output-qx quantumultx.conf --output-xyz xyz.conf
python3 -m http.server -d output 8000
```
Then import `http://<your-ip>:8000/surge.conf` or
`http://<your-ip>:8000/quantumultx.conf` in the respective app.

You can also call the converters directly from
[`src/massconfigmerger/advanced_converters.py`](src/massconfigmerger/advanced_converters.py):

```python
from massconfigmerger.advanced_converters import (
    generate_surge_conf,
    generate_qx_conf,
)

surge_data = generate_surge_conf(proxies)
qx_data = generate_qx_conf(proxies)
```

### Important Notes

- The script only runs when executed and does **not** stay running in the
  background.  Use your operating system's scheduler if you need periodic
  updates.
- When scraping Telegram make sure you only access **public** channels and
  respect Telegram's Terms of Service along with your local laws.
- All events are logged to the directory specified in `log_dir` (defaults to
  `logs/` here) so you can audit what was fetched and from where.
- On Windows consoles, colored output (like progress bars) requires the
  `colorama` library. It's included in the default dependencies, but make sure
  it's installed if you want colors.

### Docker Compose Automation

The included `docker-compose.yml` automates running the scripts. `vpn_merger`
loops every `MERGE_INTERVAL` seconds (default `86400`). Enable the optional
`aggregator` profile to fetch new links on a schedule. It runs
`massconfigmerger full` every `AGGREGATE_INTERVAL` seconds
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

### Proxy Configuration

If your network requires using an HTTP or SOCKS proxy, you can provide the
settings in two ways:

1. **Environment variables** – export `HTTP_PROXY` or `SOCKS_PROXY` before
   running the scripts:

   ```bash
   export HTTP_PROXY=http://127.0.0.1:8080
   # or
   export SOCKS_PROXY=socks5://127.0.0.1:1080
   ```


2. **Configuration file** – copy `config.yaml.example` to `config.yaml` and fill
   in the placeholder `HTTP_PROXY:` or `SOCKS_PROXY:` lines. These options work
   the same as the environment variables and are useful when running behind a
   firewall.

## Advanced Features

### Sorting by Reliability

Use `--sort-by reliability` to rank servers by past success rates recorded in
`proxy_history.json`. The file location is set by the `history_file` option in
`config.yaml`.

```bash
vpn-merger --sort-by reliability
```

### Handling Failing Sources

Each time a URL in `sources.txt` cannot be fetched, its failure count is stored
in `.failures.json` beside the list. When a source reaches the threshold number
of consecutive failures (3 by default) it is removed from `sources.txt` and
recorded in `sources_disabled.txt`. Advanced users can change the limit with
`--failure-threshold` or disable pruning entirely with `--no-prune`.

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

Run the tests with `pytest`. Install the project in editable mode with the
development extras first to ensure all dependencies are available. Skipping this
step will result in `ModuleNotFoundError` when modules like `massconfigmerger`
or the testing tools are missing. You can use the convenience requirements file
instead:

```bash
pip install -e .[dev]
# or
pip install -r requirements-dev.txt
pytest
```


## Changelog & Contributing

See [CHANGELOG.md](CHANGELOG.md) for a summary of new features and updates.
If you encounter problems or have improvements, please open an issue or submit a pull request on [GitHub](https://github.com/AmirrezaFarnamTaheri/MassConfigMerger).
For detailed contribution guidelines see [CONTRIBUTING.md](CONTRIBUTING.md).
Install the development tools with:

```bash
pip install -e .[dev]
pre-commit install
```

## Releasing a new version

1. Update the `version` field in `pyproject.toml`.
2. Add a corresponding entry at the top of `CHANGELOG.md` describing the update.
3. Commit your changes and create a git tag that matches the version:

```bash
git commit -am "Release vX.Y.Z"
git tag -a vX.Y.Z -m "vX.Y.Z"
git push && git push --tags
```

Pushing the tag triggers the `release` workflow which runs the tests, builds the
package, uploads it to PyPI using the `PYPI_API_TOKEN` secret and publishes a
GitHub release containing the generated files.
