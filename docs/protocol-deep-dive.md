### 🔑 Protocol Types and Defaults

Each server link is classified into a protocol type. By default the merger only keeps the following protocols, optimised for the Hiddify client:

- **Proxy** (HTTP/SOCKS)
- **Shadowsocks**
- **ShadowsocksR**
- **Trojan**
- **Clash** / **ClashMeta**
- **V2Ray** / **Xray**
- **Reality**
- **VMess**
- **WireGuard**
- **ECH**
- **VLESS**
- **Hysteria** / **Hysteria2**
- **TUIC**
- **Sing-box** / **Singbox**
- **ShadowTLS**

Some VPN clients may not recognise every item in this list, and other clients might support additional protocols that are omitted here. Use `--include-protocols` if you need to expand it.

-----

### Protocol Comparison

| Protocol | Key Benefit | Typical Downside |
| -------- | ----------- | ---------------- |
| **VLESS** | Flexible, supports multiple transports | Requires domain + TLS |
| **Reality** | Real HTTPS fingerprint for stealth | Needs valid certificate |
| **Trojan** | Simple TLS tunneling | Open port may be detected |
| **Shadowsocks** | Lightweight and fast | Weaker privacy guarantees |
| **WireGuard** | Kernel-level performance | Minimal obfuscation |
| **Hysteria** | QUIC based, great for high throughput | UDP may be blocked |

## 📡 Protocol Deep Dive

Below is a high-level overview of how the most common protocols work along with their strengths and weaknesses.

### Proxy (HTTP/SOCKS)
* **Mechanism**: Simple data forwarding through an intermediary server. Mostly unencrypted.
* **Pros**: Extremely lightweight and widely supported.
* **Cons**: Offers little privacy since traffic is unencrypted.
* **Use Case**: Bypassing IP blocks where encryption is not required.

### Shadowsocks
* **Mechanism**: A secure SOCKS5 proxy with traffic obfuscation. Uses symmetric encryption.
* **Pros**: Fast and simple to deploy. Works well in China and Iran.
* **Cons**: No built‑in forward secrecy and vulnerable if the shared key is known.
* **Use Case**: General browsing where moderate censorship resistance is needed.

### V2Ray / Xray (VMess & VLESS)
* **Mechanism**: A modular platform supporting multiple transports like TCP, WebSocket and gRPC.
* **Pros**: Highly configurable and supports advanced features such as multiplexing.
* **Cons**: Configuration complexity can be intimidating for new users.
* **Use Case**: Power users needing flexibility or cutting‑edge transports.

### Reality
* **Mechanism**: Uses TLS with X25519 keys to mimic ordinary HTTPS traffic while carrying encrypted payloads.
* **Pros**: Excellent stealth in hostile networks thanks to genuine TLS fingerprints.
* **Cons**: Requires a server with a real domain and valid TLS certificate.
* **Use Case**: Circumventing deep packet inspection with minimal traffic anomaly.

### Hysteria / Hysteria2
* **Mechanism**: Runs over UDP using QUIC to achieve low latency. Hysteria2 adds SMUX multiplexing.
* **Pros**: Great for high throughput and long distance connections.
* **Cons**: Some firewalls block UDP entirely which prevents use.
* **Use Case**: Gaming or high‑speed file transfers where latency matters.

### TUIC
* **Mechanism**: Another QUIC based protocol with built‑in congestion control tuned for unstable networks.
* **Pros**: Handles packet loss well and supports SMUX streams.
* **Cons**: Newer protocol with fewer client implementations.
* **Use Case**: Mobile networks or other unreliable links.

### WireGuard
* **Mechanism**: Modern VPN protocol using Curve25519 keys. Runs at kernel level on most systems.
* **Pros**: Extremely fast, lean and secure with state‑of‑the‑art cryptography.
* **Cons**: Less obfuscation compared to other protocols and requires static IP/port.
* **Use Case**: When raw performance is preferred over stealth.

### ShadowTLS
* **Mechanism**: Wraps traffic inside a legitimate TLS handshake to defeat SNI filtering.
* **Pros**: Very stealthy when paired with a real domain.
* **Cons**: Configuration can be complex and requires a working web server.
* **Use Case**: Avoiding censorship in networks that block by SNI or TLS fingerprint.

These summaries should help you pick the right protocol for your situation. Remember that not all clients support every protocol.

