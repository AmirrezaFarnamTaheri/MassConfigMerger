# 🌐 Web Interface

ConfigStream includes a modern, Flask-based web interface that provides a user-friendly dashboard for monitoring, managing, and testing your proxy configurations.

## Launching the Server

First, ensure you have installed the optional web dependencies:

```bash
pip install -e .[web]
```

Then, start the web server with the following command:

```bash
python -m configstream.web_dashboard
```

By default, the server listens on `http://127.0.0.1:8080`.

## Available Pages

The web interface is designed to be intuitive and provides a seamless experience for interacting with the core features of the toolchain.

-   **Dashboard:** A comprehensive overview of your proxy network, featuring key statistics like total sources, active proxies, success rates, and average ping. It also includes a preview of the most reliable recent proxy tests.
-   **Sources:** View and manage your list of configuration sources.
-   **History:** A detailed table of all tested proxies, their reliability, test counts, and last-tested timestamps.
-   **Analytics:** (Placeholder) This page will feature advanced data visualizations and analytics on proxy performance.
-   **Testing:** A manual testing ground to paste and test proxy configurations on the fly.
-   **Scheduler:** Monitor and manage scheduled jobs for fetching and testing proxies.
-   **Settings:** View the current application configuration derived from `config.yaml`.
-   **Help:** (Placeholder) This page will offer detailed guides and documentation.
-   **API Docs:** (Placeholder) This page will provide comprehensive documentation for the ConfigStream API.

## API Endpoints

The web interface is powered by a RESTful API. Here are the main endpoints:

-   `GET /api/current`: Returns the current test results.
-   `GET /api/history`: Returns historical test results.
- a `GET /api/statistics`: Returns aggregated statistics about the proxy configurations.
-   `GET /api/export/<format>`: Exports the proxy configurations in the specified format.
-   `GET /api/status`: Returns the system status.
-   `GET /api/logs`: Returns the application logs.
-   `GET /api/scheduler/jobs`: Returns the scheduler jobs.
-   `POST /api/test`: Allows for testing custom proxy configurations.
-   `POST /api/retest`: Retests a list of specified proxy configurations.
-   `POST /api/settings`: (Disabled by default) Can be enabled to update `config.yaml`.
-   `POST /api/sources`: Adds a new source to the sources file.