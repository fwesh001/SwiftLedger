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
            address       TEXT,
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
            text_scale    REAL DEFAULT 1.0,
            min_monthly_saving REAL DEFAULT 0.0,
            default_interest_rate REAL DEFAULT 12.0,
            loan_multiplier REAL DEFAULT 2.0,
            default_duration INTEGER DEFAULT 24,
            updated_at    DATETIME
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
            date_joined     TEXT,
            avatar_path     TEXT DEFAULT '',
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
        if "avatar_path" not in existing_columns:
            cursor.execute("ALTER TABLE members ADD COLUMN avatar_path TEXT DEFAULT '';")
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
            payment_mode    TEXT DEFAULT 'Salary Deduction',
            transfer_reference TEXT DEFAULT '',
            FOREIGN KEY(member_id) REFERENCES members(member_id)
        );
    """)

    cursor.execute("PRAGMA table_info(savings_transactions);")
    savings_columns = {row[1] for row in cursor.fetchall()}
    cursor.execute("SAVEPOINT savings_migration;")
    try:
        if "payment_mode" not in savings_columns:
            cursor.execute(
                "ALTER TABLE savings_transactions ADD COLUMN payment_mode TEXT DEFAULT 'Salary Deduction';"
            )
        if "transfer_reference" not in savings_columns:
            cursor.execute(
                "ALTER TABLE savings_transactions ADD COLUMN transfer_reference TEXT DEFAULT '';"
            )
        cursor.execute("RELEASE savings_migration;")
    except sqlite3.DatabaseError:
        cursor.execute("ROLLBACK TO savings_migration;")
        cursor.execute("RELEASE savings_migration;")
        raise

    cursor.execute("PRAGMA table_info(savings_transactions);")
    savings_columns = {row[1] for row in cursor.fetchall()}
    if "payment_mode" in savings_columns:
        cursor.execute(
            "UPDATE savings_transactions SET payment_mode = 'Salary Deduction' "
            "WHERE payment_mode IS NULL OR payment_mode = ''"
        )
    if "transfer_reference" in savings_columns:
        cursor.execute(
            "UPDATE savings_transactions SET transfer_reference = '' "
            "WHERE transfer_reference IS NULL"
        )

    # ── loans ───────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            loan_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id       INTEGER NOT NULL,
            principal       REAL NOT NULL,
            interest_rate   REAL NOT NULL,
            duration_months INTEGER NOT NULL,
            product_id      INTEGER,
            principal_paid  REAL DEFAULT 0.0,
            interest_paid   REAL DEFAULT 0.0,
            total_repaid    REAL DEFAULT 0.0,
            status          TEXT NOT NULL DEFAULT 'Active',
            due_date        DATETIME,
            date_issued     DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(member_id) REFERENCES members(member_id),
            FOREIGN KEY(product_id) REFERENCES loan_products(product_id)
        );
    """)

    # ── loan_products ──────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loan_products (
            product_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT NOT NULL UNIQUE,
            max_amount       REAL NOT NULL,
            interest_rate    REAL NOT NULL,
            duration_months  INTEGER NOT NULL,
            is_active        INTEGER DEFAULT 1,
            created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ── loan_repayments ────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loan_repayments (
            repayment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id          INTEGER NOT NULL,
            member_id        INTEGER NOT NULL,
            installment_no   INTEGER NOT NULL,
            due_date         DATETIME,
            principal_due    REAL NOT NULL,
            interest_due     REAL NOT NULL,
            total_due        REAL NOT NULL,
            principal_paid   REAL DEFAULT 0.0,
            interest_paid    REAL DEFAULT 0.0,
            total_paid       REAL DEFAULT 0.0,
            status           TEXT DEFAULT 'Pending',
            payment_date     DATETIME,
            created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(loan_id) REFERENCES loans(loan_id),
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
    if "address" not in settings_columns:
        cursor.execute("ALTER TABLE system_settings ADD COLUMN address TEXT;")
    if "min_monthly_saving" not in settings_columns:
        cursor.execute("ALTER TABLE system_settings ADD COLUMN min_monthly_saving REAL DEFAULT 0.0;")
    if "default_interest_rate" not in settings_columns:
        cursor.execute("ALTER TABLE system_settings ADD COLUMN default_interest_rate REAL DEFAULT 12.0;")
    if "loan_multiplier" not in settings_columns:
        cursor.execute("ALTER TABLE system_settings ADD COLUMN loan_multiplier REAL DEFAULT 2.0;")
    if "default_duration" not in settings_columns:
        cursor.execute("ALTER TABLE system_settings ADD COLUMN default_duration INTEGER DEFAULT 24;")
    if "updated_at" not in settings_columns:
        cursor.execute("ALTER TABLE system_settings ADD COLUMN updated_at DATETIME;")

    cursor.execute(
        "UPDATE system_settings SET address = street "
        "WHERE (address IS NULL OR address = '') AND street IS NOT NULL AND street != ''"
    )
    cursor.execute(
        "UPDATE system_settings SET street = address "
        "WHERE (street IS NULL OR street = '') AND address IS NOT NULL AND address != ''"
    )
    cursor.execute(
        "UPDATE system_settings SET security_mode = 'password' "
        "WHERE security_mode IS NULL OR TRIM(security_mode) = ''"
    )
    cursor.execute(
        "UPDATE system_settings SET security_mode = 'pin' "
        "WHERE LOWER(REPLACE(TRIM(security_mode), ' ', '_')) = 'pin'"
    )
    cursor.execute(
        "UPDATE system_settings SET security_mode = 'password' "
        "WHERE LOWER(REPLACE(TRIM(security_mode), ' ', '_')) IN ('password', 'system', 'system_auth', 'system_authentication')"
    )

    cursor.execute("PRAGMA table_info(loans);")
    loan_columns = {row[1] for row in cursor.fetchall()}
    if "status" not in loan_columns:
        cursor.execute("ALTER TABLE loans ADD COLUMN status TEXT DEFAULT 'Active';")
    if "duration_months" not in loan_columns:
        cursor.execute("ALTER TABLE loans ADD COLUMN duration_months INTEGER DEFAULT 24;")
    if "due_date" not in loan_columns:
        cursor.execute("ALTER TABLE loans ADD COLUMN due_date DATETIME;")
    if "product_id" not in loan_columns:
        cursor.execute("ALTER TABLE loans ADD COLUMN product_id INTEGER;")
    if "principal_paid" not in loan_columns:
        cursor.execute("ALTER TABLE loans ADD COLUMN principal_paid REAL DEFAULT 0.0;")
    if "interest_paid" not in loan_columns:
        cursor.execute("ALTER TABLE loans ADD COLUMN interest_paid REAL DEFAULT 0.0;")
    if "total_repaid" not in loan_columns:
        cursor.execute("ALTER TABLE loans ADD COLUMN total_repaid REAL DEFAULT 0.0;")

    cursor.execute("UPDATE loans SET due_date = date_issued WHERE due_date IS NULL;")
    cursor.execute("UPDATE loans SET principal_paid = 0.0 WHERE principal_paid IS NULL;")
    cursor.execute("UPDATE loans SET interest_paid = 0.0 WHERE interest_paid IS NULL;")
    cursor.execute("UPDATE loans SET total_repaid = 0.0 WHERE total_repaid IS NULL;")

    cursor.execute(
        """
        INSERT INTO loan_products (name, max_amount, interest_rate, duration_months)
        SELECT 'Standard Loan', 0.0, 12.0, 24
        WHERE NOT EXISTS (
            SELECT 1 FROM loan_products WHERE LOWER(name) = 'standard loan'
        )
        """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_loan_repayments_loan_status ON loan_repayments(loan_id, status);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_loan_repayments_member_due ON loan_repayments(member_id, due_date);"
    )

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
        "society_name", "street", "address", "city_state", "phone", "email",
        "reg_no", "logo_path", "security_mode", "auth_hash",
        "timeout_minutes", "show_charts", "show_alerts",
        "theme", "text_scale", "min_monthly_saving",
        "default_interest_rate", "loan_multiplier", "default_duration", "updated_at",
    }

    # Filter to only recognised columns
    filtered = {k: v for k, v in data_dict.items() if k in valid_columns}
    if "address" in filtered and "street" not in filtered:
        filtered["street"] = filtered["address"]
    if "street" in filtered and "address" not in filtered:
        filtered["address"] = filtered["street"]
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
