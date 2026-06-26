import argparse
import os
import signal
import sys
import threading
import logging
from config import load_config
from data.database_tables import create_database
from errors import AppError, ConfigurationError
from logging_config import configure_logging
from handlers.contact_handler import contact_functions
from handlers.website_handler import website_functions, view_down_history
from website_monitor import run_monitor
from handlers.integration_handler import setup_integrations

logger = logging.getLogger(__name__)


def main():
    return run_cli()


def run_cli():
    parser = argparse.ArgumentParser(description="Website Monitor")
    parser.add_argument('--run-background', action='store_true', help='Run the monitor in the background')
    parser.add_argument('--service', action='store_true', help='Run the monitor as a long-lived service')
    parser.add_argument('--config', help='Path to an INI config file')
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        configure_logging(config)
        create_database(config.database_path)
    except ValueError as exc:
        raise ConfigurationError(str(exc)) from exc

    if os.name == 'nt':
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW('Website Monitor')

    if args.run_background or args.service:
        run_service(config)
        return 0

    try:
        while True:
            print("\n1: Run Monitor")
            print("2: Setup and Integrations")
            print("3: Website Functions")
            print("4: Contact Functions")
            print("5: View website down history")
            print("0: Exit")
            choice = input("Enter your choice: ")

            if choice == '1':
                run_service(config)
            elif choice == '2':
                setup_integrations()
            elif choice == '3':
                website_functions()
            elif choice == '4':
                contact_functions()
            elif choice == '5':
                view_down_history()
            elif choice == '0':
                print("Exiting...")
                return 0
            else:
                print("Invalid choice. Please try again.")
    except KeyboardInterrupt:
        logger.info("Interrupted by user", extra={"event": "keyboard_interrupt"})
        return 130


def run_service(config):
    stop_event = threading.Event()

    def request_shutdown(signum, frame):
        logger.info("Shutdown signal received", extra={"event": "shutdown_signal"})
        stop_event.set()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    run_monitor(config=config, stop_event=stop_event)

if __name__ == "__main__":
    try:
        sys.exit(main())
    except AppError as exc:
        logging.getLogger(__name__).error(
            str(exc),
            extra={"event": exc.code, **exc.details},
        )
        sys.exit(1)
