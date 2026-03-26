from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "church.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    members_table = """
    CREATE TABLE IF NOT EXISTS members (
        member_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        ministry TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('Active', 'Inactive')),
        join_date TEXT,
        gender TEXT NOT NULL CHECK (gender IN ('Male', 'Female')),
        date_of_birth TEXT NOT NULL,
        email TEXT,
        occupational TEXT NOT NULL
    );
    """

    users_table = """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('admin', 'operator')),
        created_at TEXT NOT NULL
    );
    """

    audit_logs_table = """
    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        action TEXT NOT NULL,
        table_name TEXT,
        record_id INTEGER,
        details TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """

    with get_connection() as connection:
        connection.execute(members_table)
        connection.execute(users_table)
        connection.execute(audit_logs_table)
        connection.commit()


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")
