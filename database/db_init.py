"""
Database initialization script for SwiftLedger.
Creates SQLite tables for system_settings, members, and audit_logs.
Provides helper functions for saving settings and logging events.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict

DB_PATH = "swiftledger.db"


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Initialize the SwiftLedger SQLite database with all required tables.

    Creates the following tables if they don't already exist:
      - system_settings
      - members
      - audit_logs

    Args:
        db_path: Path to the SQLite database file (default: swiftledger.db)

    Returns:
        A sqlite3 Connection object to the database.
    """
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ── system_settings ──────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            society_name  TEXT,
            street        TEXT,
            city_state    TEXT,
            phone         TEXT,
            email         TEXT,
            reg_no        TEXT,
            logo_path     TEXT,
            security_mode TEXT,
            auth_hash     TEXT,
            timeout_minutes INTEGER DEFAULT 10
        );
    """)

    # ── members ──────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            member_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name      TEXT NOT NULL,
            phone          TEXT,
            current_savings REAL DEFAULT 0.0,
            total_loans    REAL DEFAULT 0.0
        );
    """)

    # ── audit_logs ───────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            user        TEXT,
            category    TEXT,
            description TEXT,
            status      TEXT
        );
    """)

    conn.commit()
    return conn


# ── Helper functions ─────────────────────────────────────────────────


def save_settings(data_dict: Dict[str, object], db_path: str = DB_PATH) -> None:
    """
    Insert or update a row in the system_settings table.

    If a row with id = 1 already exists it will be updated; otherwise a new
    row is inserted.  Only keys present in *data_dict* that match valid
    column names are written.

    Args:
        data_dict: A dictionary whose keys correspond to system_settings columns.
        db_path:   Path to the SQLite database file.
    """
    valid_columns = {
        "society_name", "street", "city_state", "phone", "email",
        "reg_no", "logo_path", "security_mode", "auth_hash", "timeout_minutes",
    }

    # Filter to only recognised columns
    filtered = {k: v for k, v in data_dict.items() if k in valid_columns}
    if not filtered:
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check whether a settings row already exists
    cursor.execute("SELECT COUNT(*) FROM system_settings;")
    exists = cursor.fetchone()[0] > 0

    if exists:
        set_clause = ", ".join(f"{col} = ?" for col in filtered)
        cursor.execute(
            f"UPDATE system_settings SET {set_clause} WHERE id = 1;",
            list(filtered.values()),
        )
    else:
        columns = ", ".join(filtered.keys())
        placeholders = ", ".join("?" for _ in filtered)
        cursor.execute(
            f"INSERT INTO system_settings ({columns}) VALUES ({placeholders});",
            list(filtered.values()),
        )

    conn.commit()
    conn.close()


def log_event(
    user: str,
    category: str,
    description: str,
    status: str,
    db_path: str = DB_PATH,
) -> None:
    """
    Insert a new audit-log entry into the audit_logs table.

    Args:
        user:        The user who triggered the event.
        category:    Event category (e.g. 'LOGIN', 'SETTINGS', 'LOAN').
        description: Human-readable description of the event.
        status:      Outcome status (e.g. 'SUCCESS', 'FAILURE').
        db_path:     Path to the SQLite database file.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO audit_logs (timestamp, user, category, description, status)
        VALUES (?, ?, ?, ?, ?);
        """,
        (datetime.now().isoformat(), user, category, description, status),
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    try:
        db_conn = init_db()
        print("✓ Database initialized successfully: swiftledger.db")
        db_conn.close()
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
