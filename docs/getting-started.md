---
layout: default
title: Getting Started
---

# Getting Started with ConfigStream

This guide will help you install and configure ConfigStream for the first time.

## Prerequisites

- Python 3.8 or higher
- Internet connection
- 500MB disk space (for historical data)

## Installation

### Method 1: Using pip (Recommended)

```bash
pip install configstream
```

### Method 2: From Source

```bash
git clone https://github.com/yourusername/configstream.git
cd configstream
pip install -e .
```

### Verify Installation

```bash
configstream --version
```

## Configuration

### Basic Configuration

Create a configuration file:

```bash
configstream init
```

This creates `~/.configstream/config.yaml`:

```yaml
testing:
  max_concurrent_tests: 50
  test_timeout: 5
  enable_advanced_tests: false

filtering:
  max_ping_ms: 1000
  exclude_blocked: true

output:
  formats:
    - base64
    - yaml
    - json
```

### Advanced Configuration

For advanced testing features:

```yaml
testing:
  enable_advanced_tests: true
  test_bandwidth: false  # Set true to test bandwidth (slower)
  test_network_quality: true

security:
  enable_reputation_check: true
  enable_cert_validation: true
  api_keys:
    abuseipdb: "your-api-key-here"
```

## First Run

### 1. Start the Daemon

```bash
configstream daemon --interval 2 --port 8080
```

This will:
- Run an immediate test cycle
- Schedule tests every 2 hours
- Start the web dashboard on port 8080

### 2. Access the Dashboard

Open your browser to:

```
http://localhost:8080
```

You should see the ConfigStream dashboard with:
- Statistics cards showing total nodes, success rate, etc.
- Filters for narrowing down results
- A table of all tested VPN nodes

### 3. Wait for First Test Cycle

The first test cycle runs immediately. Depending on the number of VPN sources, this may take 5-15 minutes.

Watch the logs to see progress:

```bash
# If running in foreground, you'll see logs directly
# If running in background:
tail -f daemon.log
```

## Common Tasks

### Add VPN Sources

Edit `sources.txt` and add URLs:

```
https://raw.githubusercontent.com/example/vpn/main/configs.txt
https://example.com/vpn-nodes.json
```

### Run Manual Test

```bash
configstream merge --sources sources.txt --output output.txt
```

### Export Results

From the dashboard, click "Export CSV" or "Export JSON", or use the API:

```bash
curl http://localhost:8080/api/export/csv > nodes.csv
curl http://localhost:8080/api/export/json > nodes.json
```

### View Historical Data

```bash
configstream history --days 7 --min-reliability 80
```

## Next Steps

- [Configure Advanced Testing](configuration#advanced-testing)
- [Setup Security Checks](configuration#security)
- [Deploy to Production](deployment)
- [Monitor with Prometheus](prometheus)

## Troubleshooting

### Port Already in Use

```bash
# Use a different port
configstream daemon --port 8081
```

### No Data Appearing

```bash
# Check data directory
ls -la data/

# Verify sources file exists
cat sources.txt

# Run test manually
configstream merge --sources sources.txt
```

### Performance Issues

```yaml
# Reduce concurrent tests in config.yaml
testing:
  max_concurrent_tests: 20  # Lower number
```

## Getting Help

- Check the [FAQ](faq)
- Read the [Full Documentation](/)
- Open an [Issue on GitHub](https://github.com/yourusername/configstream/issues)