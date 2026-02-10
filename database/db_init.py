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
            timeout_minutes INTEGER DEFAULT 10,
            show_charts   INTEGER DEFAULT 0,
            show_alerts   INTEGER DEFAULT 1,
            theme         TEXT DEFAULT 'dark',
            text_scale    REAL DEFAULT 1.0
        );
    """)

    # ── members ──────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            member_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_number    TEXT UNIQUE,
            full_name       TEXT NOT NULL,
            phone           TEXT DEFAULT '+234',
            bank_name       TEXT DEFAULT 'UBA',
            account_no      TEXT DEFAULT '',
            department      TEXT DEFAULT 'SLT',
            date_joined     TEXT DEFAULT (DATE('now')),
            current_savings REAL DEFAULT 0.0,
            total_loans     REAL DEFAULT 0.0
        );
    """)

    # Backfill columns for existing databases created before KYC fields were added.
    cursor.execute("PRAGMA table_info(members);")
    existing_columns = {row[1] for row in cursor.fetchall()}
    cursor.execute("SAVEPOINT members_migration;")
    try:
        if "staff_number" not in existing_columns:
            cursor.execute("ALTER TABLE members ADD COLUMN staff_number TEXT;")
        if "phone" not in existing_columns:
            cursor.execute("ALTER TABLE members ADD COLUMN phone TEXT DEFAULT '+234';")
        if "bank_name" not in existing_columns:
            cursor.execute("ALTER TABLE members ADD COLUMN bank_name TEXT DEFAULT 'UBA';")
        if "account_no" not in existing_columns:
            cursor.execute("ALTER TABLE members ADD COLUMN account_no TEXT DEFAULT '';")
        if "department" not in existing_columns:
            cursor.execute("ALTER TABLE members ADD COLUMN department TEXT DEFAULT 'SLT';")
        if "date_joined" not in existing_columns:
            cursor.execute("ALTER TABLE members ADD COLUMN date_joined TEXT;")
        if "current_savings" not in existing_columns:
            cursor.execute("ALTER TABLE members ADD COLUMN current_savings REAL DEFAULT 0.0;")
        if "total_loans" not in existing_columns:
            cursor.execute("ALTER TABLE members ADD COLUMN total_loans REAL DEFAULT 0.0;")
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_members_staff_number ON members(staff_number);"
        )
        cursor.execute("RELEASE members_migration;")
    except sqlite3.DatabaseError:
        cursor.execute("ROLLBACK TO members_migration;")
        cursor.execute("RELEASE members_migration;")
        raise

    cursor.execute("PRAGMA table_info(members);")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if "phone" in existing_columns:
        cursor.execute("UPDATE members SET phone = '+234' WHERE phone IS NULL OR phone = '';")
    if "bank_name" in existing_columns:
        cursor.execute("UPDATE members SET bank_name = 'UBA' WHERE bank_name IS NULL OR bank_name = '';")
    if "account_no" in existing_columns:
        cursor.execute("UPDATE members SET account_no = '' WHERE account_no IS NULL;")
    if "department" in existing_columns:
        cursor.execute("UPDATE members SET department = 'SLT' WHERE department IS NULL OR department = '';")
    if "date_joined" in existing_columns:
        cursor.execute(
            "UPDATE members SET date_joined = DATE('now') WHERE date_joined IS NULL OR date_joined = ''"
        )

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

    # ── savings_transactions ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS savings_transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id       INTEGER NOT NULL,
            trans_date      DATETIME DEFAULT CURRENT_TIMESTAMP,
            trans_type      TEXT NOT NULL,
            amount          REAL NOT NULL,
            running_balance REAL NOT NULL,
            FOREIGN KEY(member_id) REFERENCES members(member_id)
        );
    """)

    # ── loans ───────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            loan_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id       INTEGER NOT NULL,
            principal       REAL NOT NULL,
            interest_rate   REAL NOT NULL,
            duration_months INTEGER NOT NULL,
            status          TEXT NOT NULL DEFAULT 'Active',
            due_date        DATETIME,
            date_issued     DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(member_id) REFERENCES members(member_id)
        );
    """)

    cursor.execute("PRAGMA table_info(system_settings);")
    settings_columns = {row[1] for row in cursor.fetchall()}
    if "show_charts" not in settings_columns:
        cursor.execute("ALTER TABLE system_settings ADD COLUMN show_charts INTEGER DEFAULT 0;")
    if "show_alerts" not in settings_columns:
        cursor.execute("ALTER TABLE system_settings ADD COLUMN show_alerts INTEGER DEFAULT 1;")
    if "theme" not in settings_columns:
        cursor.execute("ALTER TABLE system_settings ADD COLUMN theme TEXT DEFAULT 'dark';")
    if "text_scale" not in settings_columns:
        cursor.execute("ALTER TABLE system_settings ADD COLUMN text_scale REAL DEFAULT 1.0;")

    cursor.execute("PRAGMA table_info(loans);")
    loan_columns = {row[1] for row in cursor.fetchall()}
    if "status" not in loan_columns:
        cursor.execute("ALTER TABLE loans ADD COLUMN status TEXT DEFAULT 'Active';")
    if "duration_months" not in loan_columns:
        cursor.execute("ALTER TABLE loans ADD COLUMN duration_months INTEGER DEFAULT 24;")
    if "due_date" not in loan_columns:
        cursor.execute("ALTER TABLE loans ADD COLUMN due_date DATETIME;")

    cursor.execute("UPDATE loans SET due_date = date_issued WHERE due_date IS NULL;")

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
        "reg_no", "logo_path", "security_mode", "auth_hash",
        "timeout_minutes", "show_charts", "show_alerts",
        "theme", "text_scale",
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
