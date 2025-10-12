# 🌐 Web Interface

The package ships with a Flask application that provides a user-friendly interface for monitoring and managing your proxy configurations.

## Launching the server

First, install the optional dependencies:

```bash
pip install configstream[web]
```

Then, start the web server with the `daemon` command:

```bash
configstream daemon
```

By default, it listens on `http://127.0.0.1:8080`.

## Pages

The web interface includes the following pages:

-   **Dashboard:** Displays a summary of your proxy configurations, including the total number of nodes, the number of successful connections, the average ping, and the number of countries. You can also filter and sort the nodes by various criteria.
-   **Export:** Allows you to export your proxy configurations in various formats, including CSV, JSON, raw text, and base64.
-   **System:** Shows the status of the application, including the scheduler jobs, system uptime, and logs.
-   **Settings:** Displays the current application settings.
-   **Documentation:** Provides detailed documentation on how to use ConfigStream.
-   **Quick Start:** A guide to getting started with ConfigStream.
-   **API Docs:** Documentation for the ConfigStream API.
-   **Roadmap:** The project roadmap.

## API Endpoints

The web interface is powered by a RESTful API. Here are the main endpoints:

-   `GET /api/current`: Returns the current test results.
-   `GET /api/history`: Returns historical test results.
-   `GET /api/statistics`: Returns aggregated statistics about the proxy configurations.
-   `GET /api/export/<format>`: Exports the proxy configurations in the specified format.
-   `GET /api/status`: Returns the system status.
-   `GET /api/logs`: Returns the application logs.
-   `GET /api/scheduler/jobs`: Returns the scheduler jobs.
-   `POST /api/settings`: Updates the application settings.
-   `POST /api/sources`: Adds a new source to the sources file.