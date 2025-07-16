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

| Protocol | Main Benefit | Downside | Typical Use Case |
| -------- | ------------ | -------- | ---------------- |
| **VMess** | Feature rich and widely supported | Distinct handshake detectable | General V2Ray clients |
| **VLESS** | Flexible transports and modern features | Requires domain & TLS | Custom transport setups |
| **Reality** | Mimics real HTTPS | Needs valid certificate | Stealth in hostile networks |
| **Shadowsocks** | Lightweight and fast | Weaker privacy | Moderate censorship bypass |
| **ShadowsocksR** | Adds protocol and obfs | Largely abandoned | Legacy SS deployments |
| **Trojan** | Simple HTTPS tunneling | Open port detected | Bypass blocks with TLS |
| **Hy2** | Hysteria2 compatibility prefix | Limited client support | Testing new Hysteria2 |
| **Hysteria** | QUIC based, high throughput | UDP often blocked | Gaming or big downloads |
| **Hysteria2** | Improved Hysteria with SMUX | UDP still blocked | Fast yet stealthy links |
| **TUIC** | QUIC with congestion control | Few implementations | Mobile or unstable links |
| **ShadowTLS** | Hides inside TLS handshake | Needs working web service | Evading SNI filtering |
| **WireGuard** | Kernel-level speed and security | Minimal obfuscation | Performance focused VPN |
| **SOCKS** | Simple generic proxy | No encryption | Basic traffic forwarding |
| **SOCKS4** | Legacy SOCKS version | No authentication | Older software proxies |
| **SOCKS5** | Auth support, widely used | Still unencrypted | Standard proxy for apps |
| **HTTP** | Works with any browser | Unencrypted and obvious | Quick proxy setup |
| **HTTPS** | Adds TLS layer | Certificate management | Proxy through port 443 |
| **gRPC** | Uses HTTP/2 semantics | Rarely supported | Multiplexed V2Ray transport |
| **WS** | Runs over ports 80/443 | Extra framing overhead | CDN or Cloudflare evasion |
| **WSS** | WebSocket over TLS | Slightly higher latency | Blend with HTTPS traffic |
| **TCP** | Ubiquitous and reliable | No obfuscation | Basic raw connections |
| **KCP** | Handles packet loss well | Requires UDP | High‑latency networks |
| **QUIC** | Fast handshake & multiplexing | UDP may be blocked | Modern UDP tunnels |
| **H2** | Multiplexed HTTP/2 layer | Limited support | Firewall evasion via 443 |

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

