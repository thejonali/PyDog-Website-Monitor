# PyDog Website Monitor

PyDog Website Monitor is a Python-based application designed to monitor the availability of websites, notify contacts when a website goes down, and provide tools for managing websites, contacts, and integrations. It is a lightweight and extensible solution for website monitoring.

## Features

- **Website Monitoring**: Continuously monitor websites and detect downtime.
- **Notifications**: Notify contacts via email or SMS when a website is down.
- **Contact Management**: Add, update, and remove contacts for notifications.
- **Website Management**: Add, update, and remove websites to be monitored.
- **Integration Management**: Configure integrations for email (SMTP/Gmail API) and SMS (Twilio).
- **Down History**: View the history of website downtimes and notifications sent.

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
├── website_monitor.py       # Core monitoring logic
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

4. Initialize the database:
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

## License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.
