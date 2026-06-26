import sqlite3

from config import load_config


def connect_database(database_path=None):
    return sqlite3.connect(database_path or load_config().database_path)
