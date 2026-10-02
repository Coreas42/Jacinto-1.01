import sqlite3
import os
from src.utils.path_helper import get_storage_path
from src.database.schema import SCHEMA_SQL, DEFAULT_DATA_SQL

DB_PATH = get_storage_path("garage_pos.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    first_time = not os.path.exists(DB_PATH)
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        if first_time:
            conn.executescript(DEFAULT_DATA_SQL)
