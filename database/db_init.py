"""
Database initialization script for SwiftLedger.
Creates SQLite tables for members, savings, loans, repayment schedules, and system settings.
"""

import sqlite3
from pathlib import Path
from typing import Optional


def initialize_database(db_path: str = "swiftledger.db") -> sqlite3.Connection:
    """
    Initialize the SwiftLedger SQLite database with all required tables.
    
    Args:
        db_path: Path to the SQLite database file (default: swiftledger.db)
        
    Returns:
        A sqlite3 Connection object to the database.
    """
    
    # Ensure database directory exists
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Create Members table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Members (
            member_id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_number TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            date_joined DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Create Savings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Savings (
            savings_id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            date DATE NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('Deduction', 'Lodgment')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES Members(member_id) ON DELETE CASCADE
        );
    """)
    
    # Create Loans table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Loans (
            loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            principal REAL NOT NULL,
            interest_rate REAL NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Active', 'Closed', 'Default')),
            date_issued DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES Members(member_id) ON DELETE CASCADE
        );
    """)
    
    # Create RepaymentSchedule table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RepaymentSchedule (
            schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER NOT NULL,
            installment_no INTEGER NOT NULL,
            expected_principal REAL NOT NULL,
            expected_interest REAL NOT NULL,
            due_date DATE NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Pending', 'Paid', 'Overdue')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (loan_id) REFERENCES Loans(loan_id) ON DELETE CASCADE,
            UNIQUE(loan_id, installment_no)
        );
    """)
    
    # Create SystemSettings table (single row for global configuration)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS SystemSettings (
            setting_id INTEGER PRIMARY KEY CHECK (setting_id = 1),
            min_monthly_saving REAL DEFAULT 0.0,
            max_loan_amount REAL DEFAULT 0.0,
            default_interest_rate REAL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Insert default system settings if not exists
    cursor.execute("SELECT COUNT(*) FROM SystemSettings;")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO SystemSettings (setting_id, min_monthly_saving, max_loan_amount, default_interest_rate)
            VALUES (1, 0.0, 0.0, 0.0);
        """)
    
    # Commit changes
    conn.commit()
    
    return conn


def close_database(conn: sqlite3.Connection) -> None:
    """
    Close the database connection.
    
    Args:
        conn: The sqlite3 Connection object to close.
    """
    if conn:
        conn.close()


if __name__ == "__main__":
    # Initialize database when script is run directly
    try:
        db_connection = initialize_database()
        print("✓ Database initialized successfully: swiftledger.db")
        close_database(db_connection)
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
