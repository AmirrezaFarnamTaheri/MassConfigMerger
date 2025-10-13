---
layout: default
title: Home
---

# ConfigStream

**Advanced VPN Configuration Aggregator & Monitoring System**

ConfigStream is a comprehensive solution for aggregating, testing, and monitoring VPN configurations with automated testing cycles, real-time dashboards, and historical performance tracking.

## Features

### 🔄 Automated Testing
- Runs tests every 2 hours automatically
- Comprehensive network quality testing
- Bandwidth measurement
- Packet loss and jitter analysis

### 📊 Real-Time Dashboard
- Beautiful web interface
- Live statistics and charts
- Advanced filtering capabilities
- Export to CSV/JSON
- Self-hosted assets for offline deployments

### 🔐 Security Checks
- IP reputation verification
- Certificate validation
- Tor/proxy detection
- Blocklist checking

### 📈 Historical Tracking
- Performance history database
- Reliability scoring
- Trend analysis
- Uptime monitoring

### 🎯 Advanced Features
- Plugin system for extensibility
- Interactive TUI
- Prometheus metrics export
- Kubernetes deployment ready

## Quick Start

### Installation

```bash
# Using pip
pip install configstream

# From source
git clone https://github.com/AmirrezaFarnamTaheri/ConfigStream
cd configstream
pip install -e .
```

### Basic Usage

```bash
# Start the daemon with web interface
configstream daemon --interval 2 --port 8080

# Run one-time test
configstream test --input configs.txt

# Merge and test configurations
configstream merge --sources sources.txt --output merged.txt
```

### Access the Dashboard

After starting the daemon, open your browser to:

```
http://localhost:8080
```

## Documentation

- [Getting Started Guide](getting-started)
- [Configuration Reference](configuration)
- [API Documentation](api)
- [Web Interface Overview](web-interface)
- [Advanced Troubleshooting](advanced-troubleshooting)

## Architecture

```mermaid
graph TD
    A[VPN Sources] --> B[Aggregator]
    B --> C[Tester]
    C --> D[Database]
    D --> E[Scheduler]
    E --> F[Web Dashboard]
    C --> G[Security Checks]
    C --> H[Network Tests]
```

## Performance

- Tests 1000+ VPN configurations in < 5 minutes
- Real-time dashboard with 2-minute refresh
- Stores unlimited historical data
- Handles concurrent testing efficiently

## Contributing

We welcome contributions! See our [Contributing Guide](contributing) for details.

## Keeping GitHub Pages in sync

This documentation site is generated directly from the Markdown files in the `docs/` folder.
The legacy static HTML bundle has been removed so GitHub Pages always renders the latest guides.
When you update the Flask templates, reflect any user-facing changes here or add a short note in
[`docs/web-interface.md`](web-interface) so the hosted documentation matches the in-app experience.

## License

MIT License - see [LICENSE](https://github.com/AmirrezaFarnamTaheri/ConfigStream/blob/main/LICENSE)

## Support

- [GitHub Issues](https://github.com/AmirrezaFarnamTaheri/ConfigStream/issues)
- [Discussions](https://github.com/AmirrezaFarnamTaheri/ConfigStream/discussions)
- [Documentation](https://amirrezafarnamtaheri.github.io/configStream/)