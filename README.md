# VPN Subscription Merger 🚀

[![CI](https://github.com/AmirrezaFarnamTaheri/MassConfigMerger/actions/workflows/ci.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/MassConfigMerger/actions/workflows/ci.yml)
[](https://opensource.org/licenses/MIT)

Welcome to the VPN Subscription Merger! This project provides a powerful Python script that automatically fetches VPN configurations from over 470 public sources, tests their connectivity, and merges them into a single, performance-sorted subscription link for use in your favorite VPN client. It can even save incremental batches while running so you always have up-to-date results.

This guide is designed for **everyone**, from absolute beginners with no coding experience to advanced users who want full automation.

> **Note**: The default protocol list is optimised for the Hiddify client. Other VPN apps may require adjusting `--include-protocols`.

**Important**: Install the dependencies with `pip install -r requirements.txt` before running **any** of the Python scripts.

### ⚡ Quick Start

1. Install **Python 3.8+** and clone this repository.
2. Run `pip install -r requirements.txt` in the project folder to install all dependencies **before running any script**.
   *For country lookups, also install the optional `geoip2` package and download the free MaxMind database.*
3. Execute `python vpn_merger.py` and wait for the `output` directory.
4. *(Optional)* pass extra flags like `--max-ping 200` or `--concurrent-limit 10` to suit your connection.
5. Import the `output/vpn_subscription_base64.txt` link (unless `--no-base64` was used) into your VPN app or load `vpn_singbox.json` in clients like sing-box.


### 🐳 Docker

Build the image and run the merger without installing Python locally:

```bash
docker build -t vpn-merger .
docker run --rm vpn-merger
```

## ✨ Key Features & Use Cases

| Feature | Description | Typical Use Case |
| ------- | ----------- | ---------------- |
| **Huge Source List** | Over 470 public subscription sources are built in. | Get a massive selection of servers with a single command. |
| **Availability Testing** | Checks each source before downloading. | Skip dead links and save time. |
| **Connectivity Testing** | Optional TCP checks measure real latency. | Prioritize servers that actually respond. |
| **Smart Sorting** | Orders the final list by reachability and speed. | Quickly pick the best server in your VPN client. |
| **Batch Saving** | Periodically saves intermediate results with `--batch-size` (default `100`). | Useful on unreliable connections. |
| **Protocol Filtering** | Use `--include-protocols` or `--exclude-protocols` to filter by protocol (defaults to the Hiddify list). | Keep only the protocols your client supports. |
| **TLS Fragment / Top N** | Use `--tls-fragment` or `--top-n` to trim the output. | Obscure SNI or keep only the fastest N entries. |
| **MUX/SMUX Tuning** | `--mux` and `--smux` modify connection multiplexing. | Improve throughput with modern clients. |
| **Resume from File** | `--resume` loads a previous raw/base64 output before fetching. | Continue a crashed run without starting over. |
| **Custom Output Dir** | Use `--output-dir` to choose where files are saved. | Organize results anywhere you like. |
| **Set Test Timeout** | Tune connection checks with `--test-timeout`. | Useful for slow or distant servers. |
| **Disable Features** | Flags `--no-url-test`, `--no-sort`, `--no-base64` and `--no-csv` give full control. | Skip slow checks or extra files when not needed. |
| **Max Ping Filter** | Remove configs with latency above `--max-ping` ms. | Keep only fast servers for gaming or streaming. |
| **Concurrent Limit / Retries** | Tweak network load with `--concurrent-limit` and `--max-retries`. | Prevent crashes on slow networks or strict hosts. |
| **Logging to File** | Save all output to a file with `--log-file`. | Useful for headless servers or debugging. |
| **Standalone or Cumulative Batches** | Use `--cumulative-batches` to keep growing files, otherwise each batch only contains new configs. | Flexible automation for heavy runs. |
| **Strict Split** | Batches are strictly capped at `--batch-size` by default. Add `--no-strict-batch` to simply trigger on size. | Control how incremental files are produced. |
| **Shuffle Sources** | `--shuffle-sources` randomizes the source order. | Helpful when using `--threshold` to avoid bias. |
| **Sing-box JSON Output** | Every batch also produces `vpn_singbox.json`. | Import directly into modern clients like sing-box/Stash. |
| **Clash YAML Output** | Generate `clash.yaml` (or `batch_*clash.yaml`) for Clash/Clash Meta users. | Works with any client supporting Clash configs. |
| **Hiddify Optimised** | Default protocols match the Hiddify client. | Other clients may reject some entries. |

### 🔍 Feature Breakdown

**Huge Source List**

> Built-in links cover hundreds of GitHub projects, Telegram channels and personal blogs. Instead of hunting for URLs yourself, you get a curated list that is updated regularly. Perfect when you need a one-click way to access lots of servers.

**Availability Testing**

> Before any downloads happen, the script checks every URL to see if it is still alive. Dead links are skipped so you don't waste time waiting on missing content.

**Connectivity Testing**

> Optionally, the script opens a real TCP connection to each server and measures the latency. This ensures the final list contains servers that actually respond and are fast enough for browsing or streaming.

**Smart Sorting**

> Configurations are sorted with reachable and low-latency servers first. Your VPN client will show the best options at the top so you can connect quickly.

**Batch Saving**

> With `--batch-size` (default `100`) you can periodically save progress. Useful on unstable networks; if the run stops, resume with `--resume` and only new servers will be fetched.

**Protocol Filtering**

> Use `--include-protocols` or `--exclude-protocols` to keep only certain technologies (e.g. just Reality) or remove unwanted ones (like Shadowsocks). By default the scripts remove any config detected as `Other`. Combine with `--tls-fragment` or `--top-n` for even finer control.

**Resume from File**

> If the process is interrupted, run again with `--resume path/to/old_output.txt` and previous results will be loaded before new sources are scanned.

**Custom Output Dir / Test Timeout / Disable Features**

> Tailor where files are saved, how long connection tests run and whether optional steps (like base64 or CSV output) run at all. These switches allow the script to fit many different environments, from low-power devices to cloud servers.

**Max Ping Filter**

> With `--max-ping` you can drop any server that responds slower than a certain number of milliseconds. Perfect for gaming or streaming when only low latency will do.

**Concurrent Limit / Retries**

> The `--concurrent-limit` and `--max-retries` options control how many requests run in parallel and how many times each download is retried. Lower the numbers on unstable networks to avoid crashes.

**Logging to File**

> Use `--log-file myrun.log` to save all console output to a file for later review. Helpful when running the script unattended on a server.

## 📖 Table of Contents

  * [How It Works](#-how-it-works)
  * [🛡️ Important Security & Privacy Disclaimer](#️-important-security--privacy-disclaimer)
  * [🛠️ How to Get Your Subscription Link (Choose One Method)](#️-how-to-get-your-subscription-link-choose-one-method)
      * [Method 1: Fully Automated with GitHub Actions (Recommended)](#method-1-fully-automated-with-github-actions-recommended)
      * [Method 2: On Your Local Computer](#method-2-on-your-local-computer)
      * [Method 3: Using Google Colab (Easy, No Setup)](#method-3-using-google-colab-easy-no-setup)
  * [📲 How to Use Your Link in VPN Apps](#-how-to-use-your-link-in-vpn-apps)
      * [Windows & Linux](#️-windows--linux)
      * [Android](#-android)
      * [macOS & iOS (iPhone/iPad)](#-macos--ios-iphoneipad)
  * [📂 Understanding the Output Files](#-understanding-the-output-files)
  * [⚙️ Advanced Usage & Troubleshooting](#️-advanced-usage--troubleshooting)

## 🧠 How It Works

The script automates a simple but powerful process to create the best possible subscription link from public sources:

1.  **📰 Gathers Sources**: It starts with a massive, built-in list of over 470 links where VPN configurations are publicly shared.
2.  **✅ Tests Source Availability**: It quickly checks each of the 470+ links to see which ones are currently online and accessible.
3.  **📥 Fetches All Configs**: It visits every active link and downloads all the individual VPN server configurations (`VLESS://`, `VMess://`, etc.).
4.  **⚡ Tests Server Performance**: This is the key step. It attempts a direct connection to each individual server to measure its real-world connection speed (latency/ping). Servers that are offline or too slow are discarded.
5.  **🧹 Cleans and Sorts**: Finally, it removes any duplicate servers and sorts the remaining, working servers from **fastest to slowest**.
6.  **📦 Generates Outputs**: It saves this final, sorted list into multiple formats, including the `base64` subscription file that you use in your app.
7.  **📁 Optional Batch Saving**: With `--batch-size` (default `100`), the script periodically saves intermediate results while it runs.

-----

## 🛡️ Important Security & Privacy Disclaimer

**Please read this carefully.**

  * **These are public servers.** The VPN configurations are sourced from public channels. You should assume that the server operators are **unknown and untrusted**.
  * **Do NOT use for sensitive data.** Do not log into banking sites, handle personal emails, or transmit any sensitive information while connected to these servers. Your traffic may not be private.
  * **For general-purpose use only.** This service is excellent for general Browse, bypassing geo-restrictions, and accessing blocked content. It is **not** a replacement for a reputable, paid VPN service if you require high security and privacy.
  * **You are using this at your own risk.** The creators of this script are not responsible for how you use these servers.

-----

## 🛠️ How to Get Your Subscription Link (Choose One Method)

### Method 1: Fully Automated with GitHub Actions (Recommended)

This is the best method. You will create a personal copy (a "fork") of this repository, and GitHub's servers will automatically run the script for you every 6 hours. This gives you a personal, auto-updating subscription link.

**Step 1: Fork the Repository**

1.  Make sure you are logged into your GitHub account.
2.  Go to the top of this repository's page.
3.  Click the **`Fork`** button. A "fork" is simply your own personal copy of a project.
4.  On the "Create a new fork" page, you can leave all the settings as they are and just click the green **`Create fork`** button.

**Step 2: Enable Workflows in Your Fork**

1.  After forking, you will be on the main page of *your* new repository. Click on the **`Actions`** tab.
2.  GitHub disables workflows on forks by default for security. You will see a yellow banner. Click the green button that says **`I understand my workflows, go ahead and enable them`**.

**Step 3: Run the Workflow for the First Time**

1.  In the left sidebar, click on the workflow named **`Merge VPN Subscriptions`**.
2.  You will see a blue banner that says "This workflow has a `workflow_dispatch` event trigger." Look to the right side of the screen and click the **`Run workflow`** dropdown button.
3.  Leave the settings as they are and click the final green **`Run workflow`** button.
4.  The script will now start running on GitHub's servers. Wait about 3-5 minutes for it to complete. You can click on the run to see its progress.

**Step 4: Get Your Personal, Permanent Subscription Link**

1.  Once the workflow is complete (it will have a green checkmark ✓), go back to the main page of your repository (the **`< > Code`** tab).
2.  You will now see a new `output` folder. Click on it.
3.  Click on the file named `vpn_subscription_base64.txt` (if you didn't use `--no-base64`).
4.  On the file view page, click the **`Raw`** button.
5.  **This is your link\!** The URL in your browser's address bar is your permanent, auto-updating subscription link. Copy it. It will look like this:
    `https://raw.githubusercontent.com/YOUR_USERNAME/CleanConfigs-SubMerger/main/output/vpn_subscription_base64.txt`

You are now ready to use this link in any VPN app\!

### Method 2: On Your Local Computer

Use this method if you want to run the script on your own machine.

**Step 1: Install Python**
If you don't have it, download from [python.org](https://www.python.org/downloads/).

> **Important**: On Windows, check the box that says "**Add Python to PATH**" during installation.

**Step 2: Download the Project**

1.  Click the green **`< > Code`** button on this page -\> **`Download ZIP`**.
2.  Extract the ZIP file to a folder on your computer.

**Step 3: Install Dependencies**

1.  Open a terminal (or `cmd` on Windows).
2.  Navigate to the project folder: `cd path/to/your/folder`.
3.  Run: `pip install -r requirements.txt`.
      * *Troubleshooting*: If you get a "permission denied" error, try `sudo pip install -r requirements.txt` on macOS/Linux, or right-click `cmd` and "Run as administrator" on Windows.

**Step 4: Run the Script**
In the same terminal, run:

```bash
python vpn_merger.py
```

After 5-15 minutes, the `output` folder will appear with your files. To use the output, upload the content of `vpn_subscription_base64.txt` (if created) somewhere (like a private [GitHub Gist](https://gist.github.com/)) and use that file's "Raw" URL.

### Method 3: Using Google Colab (Easy, No Setup)

1.  Go to [colab.research.google.com](https://colab.research.google.com) and click **`File`** -\> **`New notebook`**.
2.  Copy the entire code from the `vpn_merger.py` file in this repository.
3.  Paste it into the Colab cell and click the "Play" button (▶️).
4.  When it finishes, find the `output` folder in the file explorer on the left. Right-click the files to download them. (Like Method 2, you'll need to host the `base64.txt` file's content to get a usable link).

-----

## 📲 How to Use Your Link in VPN Apps

Here’s how to add your new subscription link to the best **free** applications.

### 🖥️ Windows & Linux

#### **App: NekoRay / NekoBox**

  * **About**: A powerful and popular client for Windows and Linux.
  * **Download**: Get it from the [NekoRay GitHub Releases](https://github.com/MatsuriDayo/nekoray/releases).

**Instructions:**

1.  Open NekoRay.
2.  From the top menu, go to **`Program`** -\> **`Add profile from URL`**.
3.  Paste your subscription link into the **`URL`** field and give it a name in the **`Name`** field.
4.  Click **`OK`**.
5.  In the main window, right-click on the new subscription group and select **`Update`**.
6.  Select a server from the list and press `Enter` to set it as active.
7.  To route your system's traffic, go to the top menu, select **`TUN Mode`**, and make sure it is checked.

### 📱 Android

#### **App 1: v2rayNG (Recommended for Beginners)**

  * **About**: The most widely used and stable V2Ray client for Android.
  * **Download**: Get it from the [Google Play Store](https://www.google.com/search?q=https://play.google.com/store/apps/details%3Fid%3Dcom.v2ray.ang) or [GitHub Releases](https://github.com/2dust/v2rayNG/releases).

**Instructions:**

1.  Open v2rayNG.
2.  Tap the **`☰`** menu icon (top-left).
3.  Select **`Subscription group setting`**.
4.  Tap the **`+`** icon (top-right).
5.  Give it a name in the **`Remark`** field (e.g., "Ultimate").
6.  Paste your subscription link into the **`URL`** field.
7.  Tap the checkmark (**`✓`**) to save.
8.  Back on the main screen, tap the three-dots menu (**`⋮`**) and select **`Update subscriptions`**.
9.  After it updates, you can run a real-world speed test by tapping the three-dots menu (**`⋮`**) -\> **`Test all configurations (real delay)`**.
10. Tap a server with good speed, then tap the large **`V`** icon at the bottom to connect.

#### **App 2: NekoBox for Android**

  * **About**: A modern client with a beautiful interface, supporting multiple protocols.
  * **Download**: Get it from [GitHub Releases](https://github.com/MatsuriDayo/NekoBoxForAndroid/releases).

**Instructions:**

1.  Open NekoBox and tap the **`Profiles`** tab at the bottom.
2.  Tap the **`+`** icon (top-right), then select **`Add subscription`**.
3.  Give the profile a name.
4.  Paste your subscription link into the **`Subscription URL`** field.
5.  Tap **`OK`**.
6.  Go back to the **`Dashboard`** tab. You'll see your new group. Tap it to select a server.
7.  Tap the floating "Connect" button in the bottom-right to connect.

### 🍎 macOS & iOS (iPhone/iPad)

#### **App: Hiddify-Next (Recommended Cross-Platform Client)**

  * **About**: A fantastic, modern, and open-source client that works on nearly every platform.
  * **Download**: Find it on the [App Store](https://www.google.com/search?q=https://apps.apple.com/us/app/hiddify-next/id6444434822) for iOS/macOS or from [GitHub](https://github.com/hiddify/hiddify-next/releases).

**Instructions (same for macOS and iOS):**

1.  Open Hiddify-Next.
2.  Tap the large **`+`** button on the main screen.
3.  Select **`Add from URL`**.
4.  Paste your subscription link into the field.
5.  Tap **`Continue`**. The app will import the profile.
6.  Select the new profile from the list.
7.  Tap the large "Connect" slider to turn it on. The app will automatically test and select the best server for you.

-----

### 🏁 Alternative Clients

There are many other applications that can import the generated subscription. Below are a few noteworthy ones:

* **Shadowrocket** (iOS)
  * **Pros**: Extremely feature rich with fine‑grained routing rules.
  * **Cons**: Paid app and only available on the App Store.
  * **Best Use**: Power users on iPhone/iPad who want maximum control.

* **Clash Meta** (Windows/macOS/Linux)
  * **Pros**: Supports a huge range of protocols and advanced rule based routing.
  * **Cons**: Configuration files can be complicated for beginners.
  * **Best Use**: Desktop users who need custom routing by domain or IP.

* **Stash** (iOS/macOS)
  * **Pros**: Built on the sing-box core with a polished interface.
  * **Cons**: Some features require a purchase.
  * **Best Use**: Users who want sing-box features on Apple devices.

* **Leaf** (macOS)
  * **Pros**: Simple GUI front‑end for Clash. Easy to get started.
  * **Cons**: Less customisation than editing Clash configs directly.
  * **Best Use**: Mac users who prefer a small native app.

Each client has its own strengths, so choose the one that fits your platform and skill level.

Users of **Clash** or **Clash Meta** can import the provided `clash.yaml` for a ready-to-use proxy list.

#### Example: import YAML into Clash Meta
1. Open **Clash Meta** and go to **Profiles**.
2. Click **Import** and select the path or URL to `vpn_clash_proxies.yaml`.
3. Enable the new profile to see all proxies.

-----

## 📂 Understanding the Output Files

| File Name                              | Purpose                                                                                                  |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `vpn_subscription_base64.txt` | *(optional)* A base64-encoded file. Most apps import directly from this file's raw URL.                  |
| `vpn_subscription_raw.txt`    | A plain text list of all the VPN configuration links.                                                    |
| `vpn_detailed.csv`            | *(optional)* A spreadsheet with detailed info about each server, including protocol, host, and ping time. |
| `vpn_report.json`             | A detailed report with all stats and configurations in a developer-friendly format.                      |
| `vpn_singbox.json`            | Outbound objects ready for import into sing-box/Stash.                                                   |
| `clash.yaml`                  | Clash configuration with all proxies and a basic group. Compatible with Clash/Clash Meta.                  |
| `vpn_clash_proxies.yaml`      | Minimal Clash YAML listing only the proxies, suitable as a provider.                                      |

-----

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

-----

During long runs, files prefixed with `cumulative_` mirror the latest results and are overwritten at each batch. Use these if you need up-to-the-minute progress.

## ⚙️ Advanced Usage & Troubleshooting

#### **Command-Line Arguments**

Run `python vpn_merger.py --help` to see all options. Important flags include:

  * `--batch-size N` - save intermediate files every `N` configs (default `100`, `0` to disable).
  * `--threshold N` - stop once `N` unique configs are collected.
  * `--no-url-test` - skip reachability testing for faster execution.
  * `--no-sort` - keep configs in the order retrieved without sorting.
  * `--top-n N` - keep only the best `N` configs after sorting.
  * `--tls-fragment TEXT` - only keep configs containing this TLS fragment.
  * `--include-protocols LIST` - comma-separated protocols to include (e.g. `VLESS,Reality`).
  * `--exclude-protocols LIST` - protocols to drop. By default `OTHER` is excluded; pass an empty string to keep everything.
  * `--exclude-pattern REGEX` - skip configs matching this regular expression (repeatable).
  * `--resume FILE` - load a previous output file before fetching new sources.
  * `--output-dir DIR` - specify where output files are stored.
  * `--test-timeout SEC` - adjust connection test timeout.
  * `--cumulative-batches` - make each batch cumulative instead of standalone.
  * `--no-strict-batch` - don't split strictly by `--batch-size`, just trigger when exceeded.
  * `--shuffle-sources` - randomize source processing order.
  * `--mux N` - set connection multiplexing level (default `8`, `0` to disable).
  * `--smux N` - set smux stream count for protocols that support it (default `4`).
  * `--geoip-db PATH` - enable country lookup using a GeoLite2 database file.

TLS fragments help obscure the real Server Name Indication (SNI) of each
connection by splitting the handshake into pieces. This makes it harder for
filtering systems to detect the destination server, especially when weak SNI
protections would otherwise expose it.

MUX and SMUX allow multiple streams to share a single connection. Higher values
can improve throughput on stable links, but may increase latency on unstable
networks. The defaults (`--mux 8` and `--smux 4`) work well for most users. Set
them to `0` to disable if compatibility issues occur.

#### **Adding Your Own Sources**

If you have your own subscription links you'd like to merge, you can add them to the script:

1.  Open the `vpn_merger.py` file in a text editor.
2.  Find the `UnifiedSources` class.
3.  Add your links to the `SOURCES` list.
4.  Save the file and run the script. If you are using the GitHub Actions method, commit the change, and the workflow will use your updated list.

#### **Retesting an Existing Output**

If you already generated a subscription file, run `python vpn_retester.py <path>` to check all servers again and sort them by current latency. The script accepts raw or base64 files and now exposes several tuning options:

* `--concurrent-limit` limit how many tests run in parallel
* `--test-timeout` set the connection timeout in seconds
* `--max-ping` drop configs slower than this ping (ms)
* `--include-protocols` or `--exclude-protocols` filter by protocol (default drops `OTHER`)
* `--output-dir` choose where results are written
* `--no-base64` / `--no-csv` disable those outputs

Example:

```bash
python vpn_retester.py output/vpn_subscription_raw.txt \
  --include-protocols VLESS,REALITY --max-ping 250 \
  --concurrent-limit 20 --test-timeout 3 --output-dir retested --no-base64
```

New files will appear in the chosen output directory:
- `vpn_retested_raw.txt`
- *(optional)* `vpn_retested_base64.txt`
- *(optional)* `vpn_retested_detailed.csv`

### 🚀 TLS Fragment, MUX & SMUX From Zero to Hero

1. **TLS Fragment** (`--tls-fragment TEXT`)
   - *Pros*: hides the full SNI during handshake which can bypass some censors.
   - *Cons*: may break older servers if they do not support fragmenting.
   - *Best Value*: a short word unique to your server, e.g. `hiddify`.
   - *Default*: none (feature off).

2. **MUX** (`--mux N`)
   - *Pros*: multiplexes many requests over one connection for speed.
   - *Cons*: high values can cause head-of-line blocking on unstable links.
   - *Best Value*: `8` works well on stable broadband.
   - *Default*: `8`.

3. **SMUX** (`--smux N`)
   - *Pros*: similar to MUX but used by Hysteria2/TUIC for UDP-like protocols.
   - *Cons*: using too many streams might waste bandwidth.
   - *Best Value*: `4` which balances speed and resource usage.
   - *Default*: `4`.

## Mass Config Aggregator Tool

This repository now includes **`aggregator_tool.py`**, a lightweight script for
quickly collecting VPN configuration links from a list of HTTP sources and a set
of Telegram channels.  It performs basic cleaning and deduplication and can run
as a Telegram bot when you need updates on demand.  Unlike `vpn_merger.py` which
focuses on speed testing, this script is meant for fast aggregation of working
links.  The tool now performs light syntax validation—for instance, Shadowsocks
and Trojan links must include an `@host:port`—and malformed entries are skipped.
It also outputs a `clash.yaml` file that works in both Clash and Clash Meta.


### Setup

1. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
2. *(Only for Telegram scraping or bot mode)* Obtain a Telegram **API ID** and
   **API Hash** from <https://my.telegram.org>.  Create your own `config.json`
   (you can copy `config.json.example`) and add them along with your bot token
   and the Telegram user IDs allowed to interact with the bot.  Alternatively
   set the environment variables `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`,
   `TELEGRAM_BOT_TOKEN` and `ALLOWED_USER_IDS`.  These variables override any
   values in your `config.json`.  The example file shows all available options.
3. Edit `sources.txt` and `channels.txt` to include any extra subscription URLs
   or channel names you wish to scrape. **Each line of `sources.txt` should
   contain exactly one valid URL with no extra text or spaces.** Each line of
   `channels.txt` may contain a full `https://t.me/...` link or just the channel
   name. Empty lines are ignored. By default the aggregator recognizes links
   starting with `vmess`, `vless`, `trojan`, `ss`,
   `ssr`, `hysteria`, `hysteria2`, `tuic`, `reality`, `naive`, `hy2` and
   `wireguard`.
4. Run the tool. The `--hours` option controls how many hours of channel history are scanned (default is 24):
   ```bash
   python aggregator_tool.py --hours 12
   ```
   The aggregated configuration links will be written to the folder specified in
   `output_dir` (default `output/`) as `merged.txt`, `merged_base64.txt`,
   `merged_singbox.json` and `clash.yaml`.
5. To enable the bot mode run (you can also pass `--hours` to control how much
   channel history is scanned):
   ```bash
   python aggregator_tool.py --bot --hours 12
   ```
   Send `/update` in your Telegram chat with the bot to trigger a run.  The bot
   will reply with the generated files.

### Configuration

`config.json` contains all runtime options (see `config.json.example` for a complete template).  The values `telegram_api_id`, `telegram_api_hash`, `telegram_bot_token` and `allowed_user_ids` may also be supplied through the environment variables `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_BOT_TOKEN` and `ALLOWED_USER_IDS`.  When set, these environment variables override any values in the file:

```json
{
  "telegram_api_id": 123456,
  "telegram_api_hash": "YOUR_HASH",
  "telegram_bot_token": "BOT_TOKEN",
  "allowed_user_ids": [11111111],
  "protocols": [
    "vmess", "vless", "trojan", "ss", "ssr", "hysteria", "hysteria2",
    "tuic", "reality", "naive", "hy2", "wireguard"
  ],
  "exclude_patterns": [],
  "output_dir": "output",
  "log_dir": "logs",
  "max_concurrent": 20
}
```

`config.json` must be a single JSON object. Only the fields shown above are
recognized—any unknown keys will cause an error. Telegram credentials are
optional unless you plan to scrape Telegram channels or run the bot mode.
When provided, environment variables take precedence over the file values.
Optional fields use these defaults when omitted:
- `protocols` – `[]`
- `exclude_patterns` – `[]`
- `output_dir` – `output`
- `log_dir` – `logs`
- `max_concurrent` – `20`

- **protocols** – only links starting with these schemes are kept.
- **exclude_patterns** – regular expressions to remove unwanted links.
- **output_dir** – where merged files are created.
- **log_dir** – daily log files are written here.
- **max_concurrent** – maximum simultaneous HTTP requests for validating and fetching sources (override with `--concurrent-limit`).

The command line options `--config`, `--sources`, `--channels`, `--output-dir`, `--concurrent-limit`, `--hours`
let you override these file locations when running the tool.

### Important Notes

- The script only runs when executed and does **not** stay running in the
  background.  Use your operating system's scheduler if you need periodic
  updates.
- When scraping Telegram make sure you only access **public** channels and
  respect Telegram's Terms of Service along with your local laws.
- All events are logged to the directory specified in `log_dir` so you can audit
  what was fetched and from where.
