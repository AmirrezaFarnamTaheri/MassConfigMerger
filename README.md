# ConfigStream

🚀 **Automated Free VPN Configuration Aggregator**

[![Merge Subscriptions](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/merge.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/merge.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

ConfigStream automatically collects, tests, and publishes working VPN configurations from free public sources. All configurations are automatically updated every 3 hours via GitHub Actions with comprehensive security testing and geolocation data.

## 🌐 Get Fresh Configurations

Visit our GitHub Pages site to download the latest tested configurations:

### **👉 [https://amirrezafarnamtaheri.github.io/ConfigStream/](https://amirrezafarnamtaheri.github.io/ConfigStream/)**

## ✨ Features

### 🤖 Fully Automated
- **Auto-updates every 3 hours** via GitHub Actions
- **Zero manual intervention** required
- **Cache-busting** ensures clients always get fresh data

### 🔒 Comprehensive Security Testing
- **Content injection detection** - Filters out proxies that modify page content
- **SSL/TLS validation** - Ensures secure HTTPS connections
- **Header preservation** - Verifies proxies don't strip important headers
- **Redirect handling** - Tests proper HTTP redirect behavior
- **Port scanning prevention** - Removes suspicious open ports

### 🌍 Rich Geolocation Data
- **Country and city** information for each proxy
- **ASN (Autonomous System Number)** details
- **Network provider** identification
- **Geographic sorting** and filtering capabilities

### ⚡ Performance Optimized
- **Latency testing** for all proxies
- **Automatic sorting** by ping time
- **Concurrent testing** with configurable workers
- **Failed proxy filtering**

### 📊 Advanced Analytics
- **Interactive proxy viewer** with filtering
- **Detailed statistics** with charts
- **Protocol distribution** analysis
- **Country distribution** visualization
- **Export capabilities** (CSV, JSON)

### 📦 Multiple Output Formats
- **Base64 Subscription** - Universal format for V2Ray clients
- **Clash YAML** - Ready-to-use Clash configuration
- **Raw Configs** - Unencoded configuration links
- **JSON Data** - Detailed proxy information with metadata
- **Statistics JSON** - Aggregated analytics data

## 🔧 How It Works

```mermaid
graph LR
    A[GitHub Actions<br/>Every 3h] -->|Trigger| B[Fetch Sources]
    B --> C[Parse Configs]
    C --> D[Test Connectivity]
    D --> E[Security Tests]
    E --> F[Geolocate]
    F --> G[Filter & Sort]
    G --> H[Generate Outputs]
    H --> I[Commit to Repo]
    I --> J[GitHub Pages<br/>Auto-Deploy]
```

### Pipeline Steps:

1. **Fetch** - Collect configurations from multiple public sources
2. **Parse** - Extract and validate proxy details
3. **Test** - Check connectivity and measure latency
4. **Secure** - Run security tests to filter malicious nodes
5. **Geolocate** - Determine country, city, and network provider
6. **Filter** - Remove non-working and insecure proxies
7. **Sort** - Order by performance (latency)
8. **Generate** - Create multiple output formats
9. **Publish** - Commit and deploy to GitHub Pages

## 📥 Available Formats

### 1. Base64 Subscription
Universal format compatible with:
- V2RayNG (Android)
- V2Box / Shadowrocket (iOS)
- V2Ray Desktop clients

**Usage:** Paste the subscription link into your client

```
https://amirrezafarnamtaheri.github.io/ConfigStream/output/vpn_subscription_base64.txt
```

### 2. Clash Configuration
Ready-to-use YAML for:
- Clash for Windows
- ClashX (macOS)
- Clash Meta / Clash Verge
- Clash Android

**Usage:** Download and import the YAML file

### 3. Raw Configs
Unencoded configuration links for:
- Manual import
- Advanced users
- Custom scripts

### 4. JSON Data
Detailed information including:
- Protocol, country, city, ASN
- Latency and performance metrics
- Security test results
- Full configuration strings

## 🛡️ Security Notice

**IMPORTANT:** These are free public VPN nodes from unknown operators.

### ❌ NOT Suitable For:
- Banking or financial transactions
- Accessing sensitive personal information
- Confidential business communications
- Medical or legal matters
- Any activity requiring guaranteed privacy

### ✅ Good For:
- Casual web browsing
- Bypassing geo-restrictions
- Accessing blocked content
- Testing and development

### 🔐 Best Practices:
- **Always use HTTPS websites** when possible
- **Never enter passwords** for important accounts
- **Avoid sensitive activities** entirely
- **Use trusted VPN services** for critical needs
- **Be aware** that traffic may be logged or modified

**Use at your own risk. No warranties provided.**

## 💻 Local Development

### Prerequisites

- Python 3.9 or higher
- pip
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/AmirrezaFarnamTaheri/ConfigStream.git
cd ConfigStream

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

### Usage

```bash
# Basic usage - fetch, test, and generate
configstream merge --sources sources.txt --output output/

# With filters
configstream merge \
  --sources sources.txt \
  --output output/ \
  --country US \
  --max-latency 500 \
  --max-workers 20

# Update GeoIP databases
configstream update-databases

# Show help
configstream --help
```

### Available Options

```
--sources          Path to sources file (required)
--output           Output directory (default: output/)
--max-proxies      Maximum number of proxies to test
--country          Filter by country code (e.g., US, DE)
--min-latency      Minimum latency in milliseconds
--max-latency      Maximum latency in milliseconds
--max-workers      Number of concurrent workers (default: 10)
--timeout          Timeout per test in seconds (default: 10)
```

## 📁 Project Structure

```
ConfigStream/
├── .github/
│   └── workflows/
│       └── merge.yml              # GitHub Actions workflow
├── src/
│   └── configstream/
│       ├── cli.py                 # Command-line interface
│       ├── core.py                # Core proxy testing logic
│       ├── pipeline.py            # Main processing pipeline
│       ├── config.py              # Configuration management
│       └── logo.svg               # Project logo
├── output/                        # Generated configs (auto-updated)
│   ├── vpn_subscription_base64.txt
│   ├── clash.yaml
│   ├── configs_raw.txt
│   ├── proxies.json               # Detailed proxy data
│   ├── statistics.json            # Aggregate statistics
│   └── metadata.json              # Update metadata
├── data/                          # GeoIP databases
├── tests/                         # Test suite
├── sources.txt                    # Source URLs
├── index.html                     # Main landing page
├── proxies.html                   # Proxy viewer
├── statistics.html                # Statistics page
├── about.html                     # Documentation
├── pyproject.toml                 # Project configuration
└── README.md                      # This file
```

## 📊 Supported Protocols

- ✅ **VMess** - V2Ray's original protocol
- ✅ **VLESS** - Lightweight V2Ray protocol (including REALITY)
- ✅ **Shadowsocks** - Fast and secure SOCKS5 proxy
- ✅ **Trojan** - TLS-based proxy protocol
- ✅ **Hysteria / Hysteria2** - UDP-based high-performance protocol
- ✅ **TUIC** - QUIC-based proxy protocol
- ✅ **WireGuard** - Modern, fast VPN protocol
- ✅ **Naive** - Censorship-resistant proxy
- ✅ **HTTP/HTTPS/SOCKS** - Traditional proxy protocols

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=configstream

# Run specific test file
pytest tests/test_core.py

# Run with verbose output
pytest -v
```

## 🔄 Automation Details

### GitHub Actions Workflow

The automation workflow (`merge.yml`) runs:
- **Every 3 hours** (00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00 UTC)
- **On manual trigger** via workflow_dispatch
- **On source file changes**

### Workflow Steps:
1. Checkout repository
2. Set up Python environment
3. Install dependencies
4. Download GeoIP databases
5. Run merge pipeline
6. Generate all output formats
7. Create metadata with cache-busting
8. Commit changes to repository
9. GitHub Pages auto-deploys

### Performance:
- Tests 1000+ configurations in ~30 minutes
- Concurrent testing with 10-20 workers
- Automatic retry for failed sources
- Efficient caching to avoid redundant tests

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### Adding New Sources

1. Fork the repository
2. Add URLs to `sources.txt` (one per line)
3. Test locally: `configstream merge --sources sources.txt`
4. Submit a pull request

### Reporting Issues

- Use [GitHub Issues](https://github.com/AmirrezaFarnamTaheri/ConfigStream/issues)
- Include relevant details (OS, Python version, error messages)
- Check if the issue already exists

### Feature Requests

- Open an issue with the "enhancement" label
- Describe the feature and use case
- Discuss implementation approach

### Code Contributions

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `pytest`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a pull request

## 📝 License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.

### What This Means:
- ✅ You can use, modify, and distribute this software
- ✅ You must include the license and copyright notice
- ✅ Any modifications must also be GPL-3.0
- ✅ Source code must be made available
- ❌ No warranty is provided

## 🙏 Acknowledgments

- **Free VPN Providers** - Thanks to all who share configurations publicly
- **Open Source Community** - For the amazing tools and libraries
- **GitHub** - For free hosting and automation
- **Contributors** - Everyone who helps improve the project

### Technologies Used:
- [Python](https://www.python.org/) - Core application
- [Sing-Box](https://sing-box.sagernet.org/) - Proxy testing backend
- [GeoIP2](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data) - Geolocation data
- [GitHub Actions](https://github.com/features/actions) - Automation
- [GitHub Pages](https://pages.github.com/) - Static hosting
- [Chart.js](https://www.chartjs.org/) - Data visualization
- [DataTables](https://datatables.net/) - Interactive tables

## 📞 Support

- 🐛 **Report Bugs:** [GitHub Issues](https://github.com/AmirrezaFarnamTaheri/ConfigStream/issues)
- 💡 **Request Features:** [GitHub Issues](https://github.com/AmirrezaFarnamTaheri/ConfigStream/issues)
- 📖 **Documentation:** [GitHub Pages](https://amirrezafarnamtaheri.github.io/ConfigStream/)
- ⭐ **Star the Project:** [GitHub Repository](https://github.com/AmirrezaFarnamTaheri/ConfigStream)

## 📈 Statistics

![GitHub Repo stars](https://img.shields.io/github/stars/AmirrezaFarnamTaheri/ConfigStream?style=social)
![GitHub forks](https://img.shields.io/github/forks/AmirrezaFarnamTaheri/ConfigStream?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/AmirrezaFarnamTaheri/ConfigStream?style=social)

---

<p align="center">
  <strong>Made with ❤️ for internet freedom</strong>
  <br>
  <sub>Educational purposes only • Use responsibly</sub>
</p>