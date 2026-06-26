# PyDog Website Monitor

PyDog Website Monitor is a Python-based application designed to monitor the availability of websites, notify contacts when a website goes down, and provide tools for managing websites, contacts, and integrations. It is a lightweight and extensible solution for website monitoring.

## Features

- **Website Monitoring**: Continuously monitor websites and detect downtime.
- **Notifications**: Notify contacts via email or SMS when a website is down.
- **Contact Management**: Add, update, and remove contacts for notifications.
- **Website Management**: Add, update, and remove websites to be monitored.
- **Integration Management**: Configure integrations for email (SMTP/Gmail API) and SMS (Twilio).
- **Down History**: View the history of website downtimes and notifications sent.
- **Incident Lifecycle**: Open an incident on first failure, avoid duplicate alerts while it remains down, and resolve it when checks recover.

## Project Structure

```
WebsiteMonitor/
├── data/
│   ├── database_tables.py   # Database schema and initialization
│   ├── webMonitor.db        # SQLite database file (ignored in version control)
├── handlers/
│   ├── contact_handler.py   # Contact management functions
│   ├── integration_handler.py # Integration setup and management
│   ├── website_handler.py   # Website management functions
├── pydog_monitor/
│   ├── config.py            # Runtime config and environment loading
│   ├── db.py                # Shared SQLite connection helper
│   ├── incidents.py         # Incident lifecycle persistence
│   ├── migrations.py        # Database migrations
│   ├── monitor.py           # Core monitoring logic
│   ├── security.py          # Secret encryption/decryption helpers
├── main.py                  # Entry point for the application
├── .gitignore               # Git ignore file
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation
```

## Prerequisites

- Python 3.7 or higher
- SQLite (comes pre-installed with Python)
- Required Python libraries (see `requirements.txt`)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd WebsiteMonitor
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Optional: enable encrypted secret storage for SMTP and Twilio credentials:
   ```bash
   python generate_fernet_key.py
   cp .env.example .env
   ```
   Then paste the generated `PYDOG_FERNET_KEY` value into `.env`.

   If `PYDOG_FERNET_KEY` is not set, the application will still run, but SMTP
   and Twilio secrets are stored as plaintext and the setup flow will warn you.

4. Optional: create a runtime config file:
   ```bash
   cp pydog.example.ini pydog.ini
   ```
   Config values load in this order: defaults, optional INI file, then
   environment variables. Use `--config pydog.ini` or set `PYDOG_CONFIG_FILE`.

5. Initialize or migrate the database:
   ```bash
   python -c "from data.database_tables import create_database; create_database()"
   ```

## Usage

Run the application:
```bash
python main.py
```

### Command-Line Options
- `--run-background`: Run the monitor in the background without the interactive menu.
- `--service`: Run the monitor as a long-lived service with graceful shutdown.
- `--config <path>`: Load runtime settings from an INI config file.

### Environment Variables
- `PYDOG_CONFIG_FILE`: Optional path to an INI config file.
- `PYDOG_DB_PATH`: SQLite database path. Defaults to `data/webMonitor.db`.
- `PYDOG_MONITOR_MIN_SLEEP_SECONDS`: Minimum monitor sleep interval.
- `PYDOG_MONITOR_MAX_SLEEP_SECONDS`: Maximum monitor sleep interval.
- `PYDOG_REQUEST_TIMEOUT_SECONDS`: HTTP request timeout.
- `PYDOG_LOG_LEVEL`: Python logging level.
- `PYDOG_LOG_FORMAT`: `text` or `json`.
- `PYDOG_FERNET_KEY`: Optional Fernet key for encrypted SMTP/Twilio secrets.

### Service and Docker Mode
Run as a service process:
```bash
python main.py --service --config pydog.ini
```

Build and run with Docker:
```bash
docker build -t pydog-website-monitor .
docker run --rm -v "$PWD/data:/app/data" --env-file .env pydog-website-monitor
```

The service handles `SIGINT` and `SIGTERM` so containers and process managers can stop it cleanly between checks.

### Interactive Menu
1. **Run Monitor**: Start monitoring websites.
2. **Setup and Integrations**: Configure email and SMS integrations.
3. **Website Functions**: Manage websites to be monitored.
4. **Contact Functions**: Manage contacts for notifications.
5. **View Website Down History**: View the history of website downtimes.
6. **Exit**: Exit the application.

## Integrations

### Email Notifications
- **Gmail API**: Follow the instructions in the application to set up Gmail API.
- **SMTP**: Configure SMTP settings for your email provider.

### SMS Notifications
- **Twilio**: Configure Twilio credentials for SMS notifications.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests to improve the project.

## Development

Install development dependencies and run tests:
```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

CI runs the same pytest suite on pushes and pull requests.

## License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.
