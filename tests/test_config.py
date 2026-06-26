from pathlib import Path

import pytest

import config as config_module
from config import load_config


CONFIG_ENV_VARS = [
    "PYDOG_CONFIG_FILE",
    "PYDOG_DB_PATH",
    "PYDOG_MONITOR_MIN_SLEEP_SECONDS",
    "PYDOG_MONITOR_MAX_SLEEP_SECONDS",
    "PYDOG_REQUEST_TIMEOUT_SECONDS",
    "PYDOG_LOG_LEVEL",
    "PYDOG_LOG_FORMAT",
]


@pytest.fixture(autouse=True)
def isolated_config_env(monkeypatch):
    monkeypatch.setattr(config_module, "load_dotenv", lambda: None)
    for env_var in CONFIG_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)


def test_load_config_uses_file_and_env_override(tmp_path, monkeypatch):
    config_file = tmp_path / "pydog.ini"
    config_file.write_text(
        "\n".join(
            [
                "[app]",
                "database_path = file.db",
                "monitor_min_sleep_seconds = 5",
                "monitor_max_sleep_seconds = 6",
                "request_timeout_seconds = 7",
                "log_level = warning",
                "log_format = json",
            ]
        )
    )
    monkeypatch.setenv("PYDOG_DB_PATH", str(tmp_path / "env.db"))

    config = load_config(config_file)

    assert config.database_path == Path(tmp_path / "env.db")
    assert config.monitor_min_sleep_seconds == 5
    assert config.monitor_max_sleep_seconds == 6
    assert config.request_timeout_seconds == 7
    assert config.log_level == "WARNING"
    assert config.log_format == "json"


def test_load_config_rejects_invalid_sleep_window(tmp_path):
    config_file = tmp_path / "pydog.ini"
    config_file.write_text(
        "\n".join(
            [
                "[app]",
                "monitor_min_sleep_seconds = 10",
                "monitor_max_sleep_seconds = 5",
            ]
        )
    )

    with pytest.raises(ValueError, match="greater than or equal"):
        load_config(config_file)
