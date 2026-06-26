import configparser
import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


CONFIG_FILE_ENV_VAR = "PYDOG_CONFIG_FILE"


@dataclass(frozen=True)
class AppConfig:
    database_path: Path
    monitor_min_sleep_seconds: int
    monitor_max_sleep_seconds: int
    request_timeout_seconds: int
    log_level: str
    log_format: str


def load_config(config_file=None):
    if load_dotenv:
        load_dotenv()

    file_values = _read_config_file(config_file or os.getenv(CONFIG_FILE_ENV_VAR))
    config = AppConfig(
        database_path=Path(_setting(file_values, "database_path", "PYDOG_DB_PATH", "data/webMonitor.db")),
        monitor_min_sleep_seconds=_int_setting(
            file_values, "monitor_min_sleep_seconds", "PYDOG_MONITOR_MIN_SLEEP_SECONDS", 180
        ),
        monitor_max_sleep_seconds=_int_setting(
            file_values, "monitor_max_sleep_seconds", "PYDOG_MONITOR_MAX_SLEEP_SECONDS", 300
        ),
        request_timeout_seconds=_int_setting(
            file_values, "request_timeout_seconds", "PYDOG_REQUEST_TIMEOUT_SECONDS", 10
        ),
        log_level=_setting(file_values, "log_level", "PYDOG_LOG_LEVEL", "INFO").upper(),
        log_format=_setting(file_values, "log_format", "PYDOG_LOG_FORMAT", "text").lower(),
    )
    _validate_config(config)
    return config


def _read_config_file(config_file):
    if not config_file:
        return {}

    path = Path(config_file)
    if not path.exists():
        raise ValueError(f"Config file does not exist: {path}")

    parser = configparser.ConfigParser()
    parser.read(path)
    return dict(parser["app"]) if parser.has_section("app") else {}


def _setting(file_values, key, env_var, default):
    return os.getenv(env_var, file_values.get(key, default))


def _int_setting(file_values, key, env_var, default):
    value = _setting(file_values, key, env_var, default)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{env_var} must be an integer.") from exc


def _validate_config(config):
    if config.monitor_min_sleep_seconds < 1:
        raise ValueError("PYDOG_MONITOR_MIN_SLEEP_SECONDS must be at least 1.")
    if config.monitor_max_sleep_seconds < config.monitor_min_sleep_seconds:
        raise ValueError("PYDOG_MONITOR_MAX_SLEEP_SECONDS must be greater than or equal to min sleep.")
    if config.request_timeout_seconds < 1:
        raise ValueError("PYDOG_REQUEST_TIMEOUT_SECONDS must be at least 1.")
    if config.log_format not in {"text", "json"}:
        raise ValueError("PYDOG_LOG_FORMAT must be either 'text' or 'json'.")
