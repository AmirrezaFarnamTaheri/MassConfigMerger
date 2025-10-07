# 🌐 Web Interface

The package ships with a small Flask application that exposes a few helper routes for running the aggregator and merger from a browser or other HTTP client.

## Launching the server

First install the optional dependencies:

This extra installs only Flask and avoids FastAPI entirely, so it works with the default Pydantic 2 dependencies.
```bash
pip install configstream[web]
```

Then start the development server with:

```bash
python -m configstream.web
```

By default it listens on `http://127.0.0.1:8080`. Use Flask's `--host` and `--port` options if you need to bind to a different address.

## Available endpoints

- `POST /api/aggregate` – run the aggregation pipeline. Returns JSON describing the output directory, generated files, and runtime duration.
- `POST /api/merge` – merge the most recent results from the aggregation step. Responds with `{"status": "merge complete"}` along with timing metadata.
- `GET /api/history` – return proxy reliability statistics as JSON for dashboards or automations.
- `GET /report` – download `vpn_report.html` if present, otherwise render the JSON report inline.
- `GET /history` – render the proxy history table with reliability badges and geo-IP metadata.

The root route (`/`) now serves a lightweight control panel. It exposes quick links to generated reports and metrics and provides buttons that drive the `POST` endpoints via the Fetch API. If you set `security.web_api_token` in `config.yaml`, the dashboard prompts for the token before dispatching the actions. The same token must be supplied with an `X-API-Key` header (or `Authorization: Bearer ...`) when invoking the endpoints programmatically.
