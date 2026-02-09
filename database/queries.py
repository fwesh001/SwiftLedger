"""
Database query operations for SwiftLedger.
Handles CRUD operations for members, savings, loans, and repayment schedules.
"""

import sqlite3
from datetime import date
from typing import Dict, List, Tuple, Optional


def add_member(db_path: str, member_data: Dict[str, str]) -> Tuple[bool, str]:
    """
    Add a new member to the Members table.
    
    Args:
        db_path: Path to the SQLite database file.
        member_data: Dictionary containing:
            - 'staff_number': Unique staff ID (required)
            - 'full_name': Member's full name (required)
            - 'date_joined': Date member joined (required, format: YYYY-MM-DD)
    
    Returns:
        A tuple (success: bool, message: str)
    """
    
    try:
        # Validate input
        required_fields = ['staff_number', 'full_name', 'date_joined']
        if not all(field in member_data for field in required_fields):
            missing = [f for f in required_fields if f not in member_data]
            return False, f"Missing required fields: {', '.join(missing)}"
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Insert new member
        cursor.execute("""
            INSERT INTO Members (staff_number, full_name, date_joined)
            VALUES (?, ?, ?)
        """, (
            member_data['staff_number'],
            member_data['full_name'],
            member_data['date_joined']
        ))
        
        # Get the inserted member's ID
        member_id = cursor.lastrowid
        
        # Commit changes
        conn.commit()
        conn.close()
        
        return True, f"Member '{member_data['full_name']}' (ID: {member_id}) added successfully."
    
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            return False, f"Error: Staff number '{member_data.get('staff_number', 'N/A')}' already exists. Please use a unique staff number."
        else:
            return False, f"Integrity error: {str(e)}"
    
    except sqlite3.DatabaseError as e:
        return False, f"Database error: {str(e)}"
    
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def get_all_members(db_path: str) -> Tuple[bool, List[Dict]]:
    """
    Retrieve all members from the Members table.
    
    Args:
        db_path: Path to the SQLite database file.
    
    Returns:
        A tuple (success: bool, members: List[Dict])
        Each member dict contains: member_id, staff_number, full_name, date_joined, created_at
    """
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        # Fetch all members
        cursor.execute("""
            SELECT member_id, staff_number, full_name, date_joined, created_at
            FROM Members
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        members = [dict(row) for row in rows]
        
        return True, members
    
    except sqlite3.DatabaseError as e:
        return False, []
    
    except Exception as e:
        return False, []


def get_member_by_id(db_path: str, member_id: int) -> Tuple[bool, Optional[Dict]]:
    """
    Retrieve a specific member by ID.
    
    Args:
        db_path: Path to the SQLite database file.
        member_id: The member's ID.
    
    Returns:
        A tuple (success: bool, member: Optional[Dict])
    """
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT member_id, staff_number, full_name, date_joined, created_at
            FROM Members
            WHERE member_id = ?
        """, (member_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return True, dict(row)
        else:
            return False, None
    
    except Exception as e:
        return False, None


def get_member_by_staff_number(db_path: str, staff_number: str) -> Tuple[bool, Optional[Dict]]:
    """
    Retrieve a specific member by staff number.
    
    Args:
        db_path: Path to the SQLite database file.
        staff_number: The member's staff number.
    
    Returns:
        A tuple (success: bool, member: Optional[Dict])
    """
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT member_id, staff_number, full_name, date_joined, created_at
            FROM Members
            WHERE staff_number = ?
        """, (staff_number,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return True, dict(row)
        else:
            return False, None
    
    except Exception as e:
        return False, None


def add_saving(db_path: str, member_id: int, amount: float, category: str) -> Tuple[bool, str]:
    """
    Add a new savings record for a member.
    
    Args:
        db_path: Path to the SQLite database file.
        member_id: The ID of the member (foreign key).
        amount: The savings amount (positive number).
        category: Either 'Deduction' or 'Lodgment'.
    
    Returns:
        A tuple (success: bool, message: str)
    """
    
    try:
        # Validate inputs
        if category not in ['Deduction', 'Lodgment']:
            return False, f"Invalid category '{category}'. Must be 'Deduction' or 'Lodgment'."
        
        if amount <= 0:
            return False, "Amount must be a positive number."
        
        if not isinstance(member_id, int) or member_id <= 0:
            return False, "Invalid member ID."
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Insert new savings record
        cursor.execute("""
            INSERT INTO Savings (member_id, amount, date, type)
            VALUES (?, ?, ?, ?)
        """, (
            member_id,
            amount,
            str(date.today()),
            category
        ))
        
        # Get the inserted savings record ID
        savings_id = cursor.lastrowid
        
        # Commit changes
        conn.commit()
        conn.close()
        
        return True, f"Savings record (ID: {savings_id}) added successfully. Amount: {amount}, Category: {category}"
    
    except sqlite3.IntegrityError as e:
        if "FOREIGN KEY constraint failed" in str(e):
            return False, f"Error: Member ID {member_id} does not exist."
        else:
            return False, f"Integrity error: {str(e)}"
    
    except sqlite3.DatabaseError as e:
        return False, f"Database error: {str(e)}"
    
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def get_member_savings(db_path: str, member_id: int) -> Tuple[bool, List[Dict]]:
    """
    Retrieve all savings records for a specific member.
    
    Args:
        db_path: Path to the SQLite database file.
        member_id: The ID of the member.
    
    Returns:
        A tuple (success: bool, savings: List[Dict])
        Each savings dict contains: savings_id, member_id, amount, date, type, created_at
    """
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        # Fetch all savings records for the member, ordered by date (newest first)
        cursor.execute("""
            SELECT savings_id, member_id, amount, date, type, created_at
            FROM Savings
            WHERE member_id = ?
            ORDER BY date DESC
        """, (member_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        savings = [dict(row) for row in rows]
        
        return True, savings
    
    except sqlite3.DatabaseError as e:
        return False, []
    
    except Exception as e:
        return False, []


if __name__ == "__main__":
    # Example usage
    db_path = "swiftledger.db"
    
    # Test add_member
    test_member = {
        'staff_number': 'EMP001',
        'full_name': 'John Doe',
        'date_joined': '2026-02-09'
    }
    
    success, message = add_member(db_path, test_member)
    print(f"Add member: {message}")
    
    # Test duplicate
    success, message = add_member(db_path, test_member)
    print(f"Add duplicate: {message}")
    
    # Test get_all_members
    success, members = get_all_members(db_path)
    if success:
        print(f"\nTotal members: {len(members)}")
        for member in members:
            print(f"  - {member['full_name']} ({member['staff_number']})")
