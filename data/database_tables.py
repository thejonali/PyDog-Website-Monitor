from pydog_monitor.config import load_config
from pydog_monitor.migrations import migrate_database


def create_database(database_path=None):
    if database_path is None:
        database_path = load_config().database_path
    migrate_database(database_path)
