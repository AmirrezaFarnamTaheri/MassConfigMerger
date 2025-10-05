# Application Architecture

This document provides a high-level overview of the MassConfigMerger application architecture.

## Architecture Diagram

The following diagram illustrates the main components of the application and their interactions:

```mermaid
graph TD
    subgraph User Interface
        CLI[CLI<br>(cli.py)]
        Web[Web UI<br>(web.py)]
    end

    subgraph Core Logic
        Commands[Commands<br>(commands.py)]
        Pipeline[Aggregation Pipeline<br>(pipeline.py)]
        Merger[VPN Merger<br>(vpn_merger.py)]
        Retester[VPN Retester<br>(vpn_retester.py)]
    end

    subgraph Data & Processing
        Config[Configuration<br>(config.py)]
        Processor[Config Processor<br>(config_processor.py)]
        Tester[Node Tester<br>(tester.py)]
        Blocklist[Blocklist Checker<br>(tester.py)]
        DB[Database<br>(db.py)]
    end

    subgraph Data Sources
        Sources[sources.txt]
        Channels[channels.txt]
    end

    subgraph Output
        OutputGenerator[Output Generator<br>(output_generator.py)]
        ReportGenerator[Report Generator<br>(report_generator.py)]
        FinalSubscription[Final Subscription Files]
    end

    CLI --> Commands
    Web --> Commands

    Commands --> Pipeline
    Commands --> Merger
    Commands --> Retester

    Pipeline --> Sources
    Pipeline --> Channels
    Pipeline --> Processor

    Merger --> Processor
    Retester --> Processor

    Processor --> Tester
    Processor --> Blocklist
    Processor --> DB

    Processor --> OutputGenerator
    Processor --> ReportGenerator

    OutputGenerator --> FinalSubscription
    ReportGenerator --> FinalSubscription

    Config -- Used by --> CLI
    Config -- Used by --> Core Logic
    Config -- Used by --> Data & Processing
```

## Component Descriptions

- **User Interface**: Provides entry points for users to interact with the application.
  - **CLI**: The command-line interface, defined in `cli.py`.
  - **Web UI**: The Flask-based web interface, defined in `web.py`.

- **Core Logic**: Orchestrates the main application workflows.
  - **Commands**: Handles the logic for the different CLI commands (`fetch`, `merge`, etc.).
  - **Aggregation Pipeline**: Manages the process of fetching configurations from various sources.
  - **VPN Merger**: Handles the process of testing, sorting, and merging configurations.
  - **VPN Retester**: Manages the process of re-testing an existing subscription file.

- **Data & Processing**: Contains the core components for data processing and testing.
  - **Configuration**: Manages the application settings.
  - **Config Processor**: A central class for filtering, testing, and normalizing configurations.
  - **Node Tester**: A utility for testing node latency and performing GeoIP lookups.
  - **Blocklist Checker**: A utility for checking IPs against a blocklist service.
  - **Database**: Manages the SQLite database for storing proxy history.

- **Data Sources**: The raw input files for the application.
  - **sources.txt**: A list of web sources for VPN configurations.
  - **channels.txt**: A list of Telegram channels for VPN configurations.

- **Output**: Handles the generation of output files.
  - **Output Generator**: Writes the final subscription files in various formats.
  - **Report Generator**: Creates reports in JSON and HTML formats.
  - **Final Subscription Files**: The generated subscription files for use in VPN clients.