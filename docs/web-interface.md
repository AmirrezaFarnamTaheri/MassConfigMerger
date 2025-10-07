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

By default it listens on `http://127.0.0.1:5000`. Use Flask's `--host` and `--port` options if you need to bind to a different address.

## Available endpoints

- `POST /aggregate` – run the aggregation pipeline. Returns JSON with the output directory and list of generated files.
- `POST /merge` – merge the most recent results. Responds with `{"status": "merge complete"}` when done.
- `GET /report` – download `vpn_report.html` if present, otherwise render the JSON report inline.

Set `security.dashboard_token` in `config.yaml` to require a shared secret for the
`/aggregate` and `/merge` routes. Supply it via the `X-ConfigStream-Token` header
or the JSON body `{ "token": "<token>" }`. When omitted, the dashboard remains
open for local automation and the token field stays optional.

The HTML dashboard issues asynchronous requests to these endpoints, displays
responses inline, and gracefully reports validation errors or missing resume
files.
