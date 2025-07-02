# Advanced VPN Methods Merger ⚡

Welcome to the **Advanced VPN Methods Merger**! This section of the project provides specialized scripts and guides for fetching, testing, and merging configurations for VPN protocols beyond the standard V2Ray ecosystem. We focus on unique tunneling and obfuscation techniques like HTTP Injector payloads, ArgoVPN's Falcon/CDN mode, and various custom tunnel/bridge methods.

## ✨ Key Features & Use Cases

| Feature                       | Description                                                          | Typical Use Case                                      |
| ----------------------------- | -------------------------------------------------------------------- | ----------------------------------------------------- |
| **Targeted Source Lists**     | Dedicated lists of public sources for each advanced protocol.        | Obtain configurations specific to HTTP Injector, ArgoVPN, etc. |
| **Protocol-Specific Parsing** | Custom logic to correctly extract host, port, and unique parameters for each advanced protocol. | Ensure proper interpretation of diverse config formats. |
| **Advanced Connectivity Testing** | Tailored tests to verify reachability and performance for each protocol. | Confirm that specialized tunnels are functional before use. |
| **Dedicated Output Formats**  | Generates output files optimized for direct import into respective clients. | Seamless integration with your preferred VPN applications. |
| **Modular Design**            | Each protocol has its own script and module for independent operation. | Run only the specific merger you need without unnecessary overhead. |

### 🔍 Feature Breakdown (Advanced)

**HTTP Injector Configs**

> *Module:* `http_injector_merger.py` – Gathers and tests configurations for **HTTP Injector**, a popular tool for custom HTTP/SSH/SSL tunnels. It parses common `.ehi` files or raw config strings (which include payload, remote proxy, SSH credentials, etc.) and outputs tested config lines ready to import into the HTTP Injector app.

**ArgoVPN (Falcon/CDN modes)**

> *Module:* `argo_merger.py` – Designed for **ArgoVPN**, an Iranian VPN that uses unique tunneling methods like **Falcon** and **Bridge (CDN)** modes through Cloudflare. It collects and verifies these specific configurations, providing alternative ways to bypass censorship by leveraging CDN networks (Cloudflare Argo Tunnels).

**Generic Tunnel & Bridge Methods**

> *Module:* `tunnel_bridge_merger.py` – Supports broader tunneling techniques, including generic SSH tunnels, simple TCP/UDP proxies, or Shadowsocks bridged over other protocols. This module uses flexible parsing and testing approaches due to the diverse nature of these methods.

## 📖 Table of Contents (Advanced)

* [🧠 How It Works (Advanced)](#-how-it-works-advanced)
* [🛡️ Important Security & Privacy Disclaimer](#%EF%B8%8F-important-security--privacy-disclaimer)
* [🛠️ How to Get Advanced Subscription Links](#%EF%B8%8F-how-to-get-advanced-subscription-links)
  * [HTTP Injector](#http-injector)
  * [ArgoVPN (Falcon/CDN)](#argovpn-falconcdn)
  * [Generic Tunnel & Bridge](#generic-tunnel--bridge)
* [📲 How to Use Your Advanced Links in VPN Apps](#-how-to-use-your-advanced-links-in-vpn-apps)
  * [Windows & Linux (Advanced)](#%EF%B8%8F-windows--linux-advanced)
  * [Android (Advanced)](#-android-advanced)
  * [macOS & iOS (Advanced)](#-macos--ios-advanced)
* [📂 Understanding the Output Files (Advanced)](#-understanding-the-output-files-advanced)
* [⚙️ Advanced Usage & Troubleshooting (Advanced)](#%EF%B8%8F-advanced-usage--troubleshooting-advanced)

## 🧠 How It Works (Advanced)

Each advanced protocol script automates a tailored process:

1. **📰 Gathers Protocol-Specific Sources:** Starts with curated lists of URLs where configurations for HTTP Injector, ArgoVPN, or generic tunnels are publicly shared. These sources might include GitHub repositories, forums, or Telegram channels.
2. **✅ Checks Source Availability:** Quickly tests each source link to ensure it's accessible before attempting to download (skips dead links to save time).
3. **📥 Fetches and Parses Configs:** Downloads the configuration data and uses custom parsing logic for the specific format of each protocol. For example, HTTP Injector configs might be base64 encoded payloads, whereas ArgoVPN might just provide domain names.
4. **⚡ Performs Connectivity Tests:** For each config, the script attempts a connection or protocol-specific ping to measure performance. Offline or slow servers are marked accordingly or discarded.
5. **🧹 Cleans and Sorts Results:** Removes duplicate entries and sorts the working servers by performance (e.g., lowest latency first).
6. **📦 Generates Output Files:** Saves the consolidated list into one or more output files (like a text list of configs, JSON with details, etc.) ready to be imported into the respective VPN client.

-----

## 🛡️ Important Security & Privacy Disclaimer

*Using third-party configs from public sources comes with risks.* Always be cautious: some config links might be malicious or monitored. Test advanced configs in a safe environment first, and avoid entering personal information or credentials into untrusted apps. **Your security is your responsibility.**

## 🛠️ How to Get Advanced Subscription Links

Each advanced protocol has its own script. Run them independently as needed:

### HTTP Injector

1. **Install Python** and the required dependencies (`pip install -r requirements.txt`).
2. **Run the merger script:**
   ```bash
   python advanced_methods/http_injector_merger.py
   ```
3. Wait for the script to finish. Find the output files in an `output/http_injector/` directory (e.g., a text file containing merged HTTP Injector configs).

### ArgoVPN (Falcon/CDN)

1. **Install Python** and dependencies.
2. **Run the merger script:**
   ```bash
   python advanced_methods/argo_merger.py
   ```
3. When done, check `output/argo/` for output files (e.g., a list of domains or Argo config strings).

### Generic Tunnel & Bridge

1. **Install Python** and dependencies.
2. **Run the merger script:**
   ```bash
   python advanced_methods/tunnel_bridge_merger.py
   ```
3. Upon completion, look into `output/tunnel_bridge/` for the results (e.g., `tunnels_raw.txt` with a list of working tunnels).

*(You can also integrate these into automation workflows similar to the main script, e.g., create separate GitHub Actions or Colab notebooks for each advanced method if needed.)*

## 📲 How to Use Your Advanced Links in VPN Apps

After obtaining the merged configurations, you'll need to import or input them into the appropriate VPN applications. Below are general guidelines for each type:

### Windows & Linux (Advanced)

Depending on the protocol, you might use different client software:

* **HTTP Injector:** On PC, you may use alternative tools or command-line SSH/Proxy clients that mimic HTTP Injector behavior.
* **ArgoVPN:** Currently, ArgoVPN is primarily mobile-focused. If a desktop version exists or if using Cloudflare WARP, you would configure Cloudflare client with the provided domains.
* **SSH/Tunnels:** Use an SSH client or proxy client (like `proxytunnel` or `ssh` command with -D for dynamic forwarding) with the credentials provided.

### Android (Advanced)

#### HTTP Injector App

* **App:** HTTP Injector (by Evozi) – a popular Android app for custom payload VPNs.
* **Download:** Available on Google Play or as an APK from the official site.
* **Using the Config:** If the output is a raw config text file (e.g., `vpn_http_injector_raw.txt`):
  1. Copy the content of the file.
  2. Open HTTP Injector and navigate to the import/config section.
  3. Paste the config or use the import function if a specific format (.ehi) file was generated.
     If an `.ehi` file is produced, transfer it to your device and use HTTP Injector's *Import Config* feature.

#### ArgoVPN App

* **App:** ArgoVPN – an Iran-focused VPN app with Falcon and Bridge modes.
* **Download:** Officially from the [ArgoVPN website](https://argovpn.com) or a trusted app store.
* **Using the Config:** The script likely produces a domain list for Falcon or bridge addresses:
  1. Open ArgoVPN and go to the **Connections Type** or **Falcon** section.
  2. For Falcon mode, find the option to **Add Custom Domain** (as Falcon allows users to add their own domain) and input one of the domains from the output list.
  3. For Bridge mode, look for an option to import or add bridge servers and use the provided addresses.

### macOS & iOS (Advanced)

* **HTTP Injector:** There is no official HTTP Injector on iOS/macOS, but you might use equivalent tools (e.g., custom VPN client that supports SSH/HTTP proxy).
* **ArgoVPN:** As of now, ArgoVPN is Android-only. iOS users might need to use alternatives or manual Cloudflare WARP setup.
* **SSH/Tunnels:** On macOS/iOS, advanced users can use the built-in `ssh` in Terminal (macOS) or apps like Secure ShellFish (iOS) to create SSH tunnels using the provided configs.

## 📂 Understanding the Output Files (Advanced)

Each advanced merger script will create output files, usually in a dedicated subfolder under `output/`. Here are examples of what to expect:

| File Name                  | Purpose                                                                                            |
| -------------------------- | -------------------------------------------------------------------------------------------------- |
| `http_injector_merged.txt` | Plain text file of merged HTTP Injector config lines (ready to import or open with HTTP Injector). |
| `argo_falcon_domains.txt`  | List of domain names usable in ArgoVPN Falcon mode.                                                |
| `tunnels_raw.txt`          | Raw list of tunnel endpoints (SSH/tcp/udp) that were found working.                                |
| `[protocol]_detailed.csv`  | (If generated) CSV with details for each server (host, port, latency, etc.).                       |
| `[protocol]_report.json`   | (If generated) JSON report with statistics and details for the run.                                |

## ⚙️ Advanced Usage & Troubleshooting (Advanced)

Each advanced script supports a subset of command-line arguments similar to `vpn_merger.py`. Use the `--help` flag to see available options. For example:

```bash
python advanced_methods/http_injector_merger.py --help
```

This will show usage instructions specific to the HTTP Injector merger (such as flags for output directory or test timeout, if implemented).

**Common Issues & Tips:**

* **HTTP Injector Config Not Working:** Ensure the config format is correct for the app. Sometimes extra spaces or lines can cause the import to fail. Also, configs may expire quickly if they rely on temporary SSH accounts.
* **ArgoVPN Connection Fails:** The Falcon domain might have to be one that you registered with ArgoVPN's system. If the provided public domains don't work, ArgoVPN may require your own domain setup.
* **SSH Tunnel Issues:** If testing SSH tunnels, you might hit rate limits or require SSH key authentication instead of passwords. Consider using known-good SSH accounts and check that the host is reachable on the given port (often 22 or 443).

*(Further troubleshooting steps should be added as these features are tested and user feedback is received.)*
