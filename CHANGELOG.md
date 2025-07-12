# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and the project adheres to [Semantic Versioning](https://semver.org/).

## [0.4.0] - 2025-07-12
### Added
- Unit tests for configuration parsing and deduplication.
- Improved Telegram configuration handling.

## [0.5.0] - 2025-07-13
### Added
- Failure tracking for aggregator sources. Entries are only pruned after three consecutive failures.
- `--no-prune` flag to disable automatic pruning.

## [0.3.0] - 2025-07-12
### Added
- Continuous integration workflow on GitHub Actions.
- Support for running without Telegram credentials.
- Reconnection logic for Telegram scraping.

## [0.2.0] - 2025-07-11
### Added
- `aggregator_tool.py` for collecting VPN configs from URLs and Telegram channels.
- Concurrency limits and hour-based history lookups.

## [0.1.0] - 2025-06-30
### Added
- Initial release with `vpn_merger.py` and basic merging features.

