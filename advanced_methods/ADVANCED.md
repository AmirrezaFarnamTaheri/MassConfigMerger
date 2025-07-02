# Advanced Methods

This document outlines optional features for power users.

## Using a Proxy

Use `--proxy` to fetch subscription sources through an HTTP or SOCKS proxy. Example for Tor:

```bash
python vpn_merger.py --proxy socks5://127.0.0.1:9050
```

## Full TLS Testing

Pass `--full-test` to perform a TLS handshake when verifying each server. This can help detect blocked or misconfigured nodes but increases runtime.
