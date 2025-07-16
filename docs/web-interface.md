# 🌐 Web Interface

The package ships with a small Flask application that exposes a few helper routes for running the aggregator and merger from a browser or other HTTP client.

## Launching the server

First install the optional dependencies:

This extra installs only Flask and avoids FastAPI entirely, so it works with the default Pydantic 2 dependencies.
```bash
pip install massconfigmerger[web]
```

Then start the development server with:

```bash
python -m massconfigmerger.web
```

By default it listens on `http://127.0.0.1:5000`. Use Flask's `--host` and `--port` options if you need to bind to a different address.

## Available endpoints

- `GET /aggregate` – run the aggregation pipeline. Returns JSON with the output directory and list of generated files.
- `GET /merge` – merge the most recent results. Responds with `{"status": "merge complete"}` when done.
- `GET /report` – download `vpn_report.html` if present, otherwise render the JSON report inline.

These routes are intentionally simple and return minimal information, making them suitable for automation or quick checks from a web browser.
