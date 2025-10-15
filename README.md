# ConfigStream

🚀 **Automated Free VPN Configuration Aggregator**

[![Merge Subscriptions](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/merge.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/merge.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

ConfigStream automatically collects, tests, and publishes working VPN configurations from free public sources. All configurations are automatically updated every 6 hours via GitHub Actions.

## 🌐 Get Fresh Configurations

Visit our GitHub Pages site to download the latest tested configurations:

### **👉 [https://amirrezafarnamtaheri.github.io/ConfigStream/](https://amirrezafarnamtaheri.github.io/ConfigStream/)**

## 📥 Available Formats

- **Base64 Subscription** - Universal format compatible with V2RayNG, V2Box, and similar clients
- **Clash YAML** - Ready-to-use configuration for Clash and Clash Meta
- **Raw Configs** - Plain text configuration links

## ✨ Features

- ✅ **Automatic Updates** - Fresh configurations every 6 hours
- ✅ **Performance Testing** - All configs tested before publishing
- ✅ **Multiple Formats** - Support for various VPN clients
- ✅ **Latency Sorting** - Configs sorted by performance
- ✅ **Open Source** - Fully transparent and auditable
- ✅ **Zero Setup** - Just grab the subscription link and go

## 🔧 How It Works

```mermaid
graph LR
    A[GitHub Actions] -->|Every 6h| B[Fetch Sources]
    B --> C[Test Configs]
    C --> D[Filter & Sort]
    D --> E[Generate Outputs]
    E --> F[Commit to Repo]
    F --> G[GitHub Pages]
```

1. **GitHub Actions** triggers every 6 hours
2. **Fetches** VPN configurations from multiple public sources
3. **Tests** each configuration for connectivity and latency
4. **Filters** out non-working configs
5. **Sorts** by performance (ping time)
6. **Generates** multiple output formats
7. **Commits** to repository automatically
8. **Publishes** via GitHub Pages

## ⚠️ Security Disclaimer

**IMPORTANT:** These are free public VPN nodes from unknown operators.

- ❌ **NOT for banking** or sensitive activities
- ❌ **Traffic may be logged** or modified
- ❌ **No privacy guarantees**
- ✅ **Good for casual browsing** and bypassing geo-restrictions
- ✅ **Use HTTPS** websites when possible

**Use at your own risk. Read our [full disclaimer](docs/tutorial.md#-important-security--privacy-disclaimer).**

## 💻 Local Development

### Prerequisites

- Python 3.8 or higher
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/AmirrezaFarnamTaheri/ConfigStream.git
cd ConfigStream

# Install in development mode
pip install -e .
```

### Usage

```bash
# Fetch and merge configurations
configstream merge --sources sources.txt --output output/

# Fetch only (no testing)
configstream fetch --sources sources.txt --output fetched.txt

# Retest existing configs
configstream retest --input configs.txt --output tested.txt

# Add a new source
configstream sources add https://example.com/configs.txt

# List all sources
configstream sources list
```

## 📁 Project Structure

```
ConfigStream/
├── .github/
│   └── workflows/
│       └── merge.yml              # Automated workflow
├── src/
│   └── configstream/
│       ├── cli.py                 # Command-line interface
│       ├── commands.py            # CLI command handlers
│       ├── vpn_merger.py          # Main merge logic
│       ├── tester.py              # Connection tester
│       ├── output_writer.py       # Output generator
│       └── core/                  # Core modules
├── tests/                         # Test suite
├── output/                        # Generated configs (auto-updated)
├── sources.txt                    # Source URLs
├── index.html                     # GitHub Pages landing
└── README.md
```

## 🛠️ Configuration

Create `config.yaml` for custom settings:

```yaml
sources:
  sources_file: sources.txt

testing:
  timeout: 5
  max_workers: 20
  test_url: "http://www.gstatic.com/generate_204"

output:
  output_dir: output
  base64_file: vpn_subscription_base64.txt
  clash_file: clash.yaml
  raw_file: configs_raw.txt

filtering:
  include_protocols:
    - vmess
    - vless
    - trojan
    - shadowsocks
  min_ping_ms: null
  max_ping_ms: 2000
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=configstream

# Run specific test
pytest tests/test_vpn_merger.py
```

## 📊 Supported Protocols

- ✅ VMess
- ✅ VLESS (including REALITY)
- ✅ Trojan
- ✅ Shadowsocks
- ✅ SSR (ShadowsocksR)
- ✅ Hysteria / Hysteria2
- ✅ TUIC
- ✅ Naive

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Thanks to all free VPN providers
- Built with Python and GitHub Actions
- Powered by the open-source community

## 📞 Support

- 🐛 [Report a Bug](https://github.com/AmirrezaFarnamTaheri/ConfigStream/issues)
- 💡 [Request a Feature](https://github.com/AmirrezaFarnamTaheri/ConfigStream/issues)
- ⭐ Star this repo if you find it useful!

---

**Made with ❤️ for internet freedom** | **Educational purposes only**