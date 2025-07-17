## ⚙️ Advanced Usage & Troubleshooting

#### **Command-Line Arguments**

Run `python vpn_merger.py --help` to see all options. Important flags include:

  * `--save-every N` - save intermediate files every `N` configs (default `100`, `0` to disable).
  * `--stop-after-found N` - stop once `N` unique configs are collected.
  * `--no-url-test` - skip reachability testing for faster execution.
  * `--no-sort` - keep configs in the order retrieved without sorting.
  * `--top-n N` - keep only the best `N` configs after sorting.
  * `--tls-fragment TEXT` - only keep configs containing this TLS fragment.
  * `--include-protocols LIST` - comma-separated protocols to include (e.g. `VLESS,Reality`).
    Valid protocol names: `VMESS`, `VLESS`, `SHADOWSOCKS`, `SHADOWSOCKSR`,
    `TROJAN`, `HYSTERIA2`, `HYSTERIA`, `TUIC`, `REALITY`, `NAIVE`, `JUICITY`,
    `WIREGUARD`, `SHADOWTLS`, `BROOK`, and `OTHER`.
  * `--exclude-protocols LIST` - protocols to drop. By default `OTHER` is excluded; pass an empty string to keep everything.
  * `--exclude-pattern REGEX` - skip configs matching this regular expression (repeatable).
  * `--include-pattern REGEX` - only keep configs matching this regular expression (repeatable).
    These pattern flags also apply to `aggregator-tool`.
  * `--resume FILE` - load a previous output file before fetching new sources.
  * `--sources FILE` - read subscription URLs from a custom file (default `sources.txt`).
  * `--output-dir DIR` - specify where output files are stored.
  * `--connect-timeout SEC` - adjust connection test timeout (sets `connect_timeout`).
  * `--cumulative-batches` - make each batch cumulative instead of standalone.
  * `--no-strict-batch` - don't split strictly by `--save-every`, just trigger when exceeded.
  * `--shuffle-sources` - randomize source processing order.
  * `--mux N` - set connection multiplexing level (default `8`, `0` to disable).
  * `--smux N` - set smux stream count for protocols that support it (default `4`).
  * `--geoip-db PATH` - enable country lookup using a GeoLite2 database file.
  * `--include-country LIST` - comma-separated ISO codes to keep when `--geoip-db` is set.
  * `--exclude-country LIST` - ISO codes to drop when `--geoip-db` is set.

TLS fragments help obscure the real Server Name Indication (SNI) of each
connection by splitting the handshake into pieces. This makes it harder for
filtering systems to detect the destination server, especially when weak SNI
protections would otherwise expose it.

MUX and SMUX allow multiple streams to share a single connection. Higher values
can improve throughput on stable links, but may increase latency on unstable
networks. The defaults (`--mux 8` and `--smux 4`) work well for most users. Set
them to `0` to disable if compatibility issues occur.

#### **Adding Your Own Sources**

If you have your own subscription links you'd like to merge, edit `sources.txt`:

1.  Open the `sources.txt` file in a text editor.
2.  Add one URL per line (blank lines are ignored).
3.  Save the file and run the script. If you are using the GitHub Actions method, commit the change so the workflow uses your updated list.

#### **Retesting an Existing Output**

If you already generated a subscription file, run `python vpn_retester.py <path>` to check all servers again and sort them by current latency. The script accepts raw or base64 files and now exposes several tuning options:

* `--concurrent-limit` limit how many tests run in parallel
* `--connect-timeout` set the connection timeout in seconds (stored in `connect_timeout`)
* `--max-ping` drop configs slower than this ping (ms)
* `--include-protocols` or `--exclude-protocols` filter by protocol (default drops `OTHER`)
* `--output-dir` choose where results are written
* `--no-base64` / `--no-csv` disable those outputs

Example:

```bash
python vpn_retester.py output/vpn_subscription_raw.txt \
  --include-protocols VLESS,REALITY --max-ping 250 \
  --concurrent-limit 20 --connect-timeout 3 --output-dir retested --no-base64
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

### Running the tests

If you want to run the project's unit tests, **install the development
dependencies first**. You can either install the package in editable mode with
the `dev` extras or use the provided `requirements-dev.txt` file before
invoking `pytest`:

> **Important**: run `pip install -e .[dev]` (or
> `pip install -r requirements-dev.txt`) before executing `pytest`. The
> `pytest_asyncio` plugin and other test requirements are only installed with
> these development dependencies.

```bash
pip install -e .[dev]
# or
pip install -r requirements-dev.txt
pytest
```

Failing to install the `dev` extras first will result in `ModuleNotFoundError`
when the test suite tries to import `massconfigmerger`.

