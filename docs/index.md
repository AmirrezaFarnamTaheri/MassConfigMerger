# ConfigStream Documentation

## Quick Start

ConfigStream is an advanced VPN configuration aggregator with real-time monitoring, testing, and reliability tracking.

### Installation

```bash
pip install configstream
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

## Features

- **Automated Testing**: Runs every 2 hours automatically
- **Web Dashboard**: Real-time monitoring with filtering
- **Advanced Testing**: Bandwidth, packet loss, jitter
- **Security Checks**: IP reputation, certificate validation
- **Historical Tracking**: Performance history and reliability scores
- **Export Capabilities**: CSV, JSON export with filtering

## API Documentation

### REST API Endpoints

#### GET /api/current
Returns current test results.

Query parameters:
- `protocol`: Filter by protocol
- `country`: Filter by country
- `min_ping`: Minimum ping (ms)
- `max_ping`: Maximum ping (ms)
- `exclude_blocked`: Exclude blocked nodes

#### GET /api/statistics
Returns aggregated statistics.

#### GET /api/history?hours=24
Returns historical test data.

#### GET /api/export/{format}
Export data (csv, json).

## Configuration

See [Configuration Guide](configuration.md) for detailed settings.

## Architecture

See [Architecture Documentation](architecture.md) for system design.