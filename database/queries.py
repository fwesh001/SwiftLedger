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


def get_total_savings(db_path: str, member_id: int) -> Tuple[bool, float]:
    """
    Calculate total savings for a member (Lodgments positive, Deductions negative).

    Returns (True, total_amount) on success or (False, 0.0) on error.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute(
            """
            SELECT COALESCE(SUM(CASE WHEN type = 'Lodgment' THEN amount
                                      WHEN type = 'Deduction' THEN -amount
                                      ELSE 0 END), 0.0) as total
            FROM Savings
            WHERE member_id = ?
            """,
            (member_id,)
        )
        row = cursor.fetchone()
        conn.close()

        total = float(row[0]) if row and row[0] is not None else 0.0
        return True, total

    except sqlite3.DatabaseError:
        return False, 0.0
    except Exception:
        return False, 0.0


def get_system_settings(db_path: str) -> Tuple[bool, Optional[Dict]]:
    """
    Retrieve current system settings from the SystemSettings table.

    Returns (True, settings_dict) on success or (False, None) on error.
    The settings dict contains: min_monthly_saving, max_loan_amount,
    default_interest_rate, loan_multiplier, default_duration.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT min_monthly_saving, max_loan_amount, default_interest_rate,
                   loan_multiplier, default_duration, updated_at
            FROM SystemSettings
            WHERE setting_id = 1
            """
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            settings = dict(row)
            # Provide sensible defaults if columns are missing (for older DBs)
            settings.setdefault('loan_multiplier', 2.0)
            settings.setdefault('default_duration', 24)
            settings.setdefault('default_interest_rate', 12.0)
            return True, settings
        else:
            # No settings row; return defaults
            return True, {
                'min_monthly_saving': 0.0,
                'max_loan_amount': 0.0,
                'default_interest_rate': 12.0,
                'loan_multiplier': 2.0,
                'default_duration': 24,
                'updated_at': None,
            }

    except sqlite3.DatabaseError:
        return False, None
    except Exception:
        return False, None


def calculate_repayment_schedule(principal: float, annual_rate: float, duration_months: int = 24) -> List[Dict]:
    """
    Calculate a repayment schedule with the following rules:
    - Month 1: principal_payment = 0, interest on full principal (interest-only month)
    - Months 2 to duration_months: equal principal payments with interest on remaining balance

    Args:
        principal: The loan principal amount.
        annual_rate: Annual interest rate as a percentage (e.g., 12 for 12%).
        duration_months: Total number of months (default 24).

    Returns:
        A list of dictionaries, each containing:
        - month_number
        - principal_payment
        - interest_payment
        - total_payment
        - remaining_balance
    """
    schedule = []
    monthly_rate = annual_rate / 100.0 / 12.0
    remaining_balance = principal

    # Number of principal-paying months (excludes the interest-only first month)
    principal_paying_months = duration_months - 1
    if principal_paying_months <= 0:
        principal_paying_months = 1  # Edge case: if duration is 1, pay it all

    # Calculate base monthly principal payment (rounded to 2 decimals)
    base_principal_payment = round(principal / principal_paying_months, 2)

    for month in range(1, duration_months + 1):
        if month == 1:
            # Month 1: interest-only
            principal_payment = 0.0
            interest_payment = round(remaining_balance * monthly_rate, 2)
        else:
            # Months 2+: principal + interest on remaining balance
            # Last month: pay off the exact remaining balance to avoid rounding errors
            if month == duration_months:
                principal_payment = round(remaining_balance, 2)
            else:
                principal_payment = base_principal_payment

            interest_payment = round(remaining_balance * monthly_rate, 2)
            remaining_balance -= principal_payment

        total_payment = round(principal_payment + interest_payment, 2)

        # Ensure remaining balance doesn't go negative due to rounding
        if remaining_balance < 0:
            remaining_balance = 0.0

        schedule.append({
            'month_number': month,
            'principal_payment': principal_payment,
            'interest_payment': interest_payment,
            'total_payment': total_payment,
            'remaining_balance': round(remaining_balance, 2),
        })

    # Final sanity check: force last month's remaining balance to exactly 0
    if schedule:
        schedule[-1]['remaining_balance'] = 0.0

    return schedule


def generate_repayment_schedule(db_path: str, loan_id: int, principal: float, interest_rate: float, months: int = 24) -> Tuple[bool, str]:
    """
    Generate a simple repayment schedule for a loan.

    This is a placeholder implementation that creates `months` equal installments
    with fixed principal portion and fixed interest per month based on the original principal.
    """
    try:
        from datetime import date, timedelta

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Basic equal principal split
        principal_per_installment = round(principal / months, 2)
        monthly_interest = round((principal * (interest_rate / 100.0)) / 12.0, 2)

        start_date = date.today()

        for i in range(1, months + 1):
            due_date = start_date + timedelta(days=30 * i)
            cursor.execute(
                """
                INSERT OR IGNORE INTO RepaymentSchedule
                    (loan_id, installment_no, expected_principal, expected_interest, due_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    loan_id,
                    i,
                    principal_per_installment,
                    monthly_interest,
                    str(due_date),
                    'Pending',
                ),
            )

        conn.commit()
        conn.close()
        return True, "Repayment schedule generated"

    except sqlite3.DatabaseError as e:
        return False, f"Database error generating schedule: {e}"
    except Exception as e:
        return False, f"Unexpected error generating schedule: {e}"


def apply_for_loan(
    db_path: str,
    member_id: int,
    principal: float,
    interest_rate: Optional[float] = None,
    duration: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Attempt to create a loan for a member, enforcing the dynamic savings-multiplier rule.

    Args:
        db_path: Path to the SQLite database.
        member_id: The member applying for the loan.
        principal: Requested loan amount.
        interest_rate: Annual interest rate (%). If None, uses SystemSettings.default_interest_rate.
        duration: Number of months for repayment. If None, uses SystemSettings.default_duration.

    Returns:
        (True, success_message) on success or (False, error_message) on failure.
        The loan record stores the actual interest_rate applied (audit trail).
    """
    try:
        # Fetch system settings for dynamic rules
        settings_ok, settings = get_system_settings(db_path)
        if not settings_ok or settings is None:
            return False, "Failed to retrieve system settings"

        # Apply defaults from settings if not provided
        loan_multiplier = float(settings.get('loan_multiplier', 2.0))
        actual_interest_rate = interest_rate if interest_rate is not None else float(settings.get('default_interest_rate', 12.0))
        actual_duration = duration if duration is not None else int(settings.get('default_duration', 24))

        # Get total savings for validation
        ok, total_savings = get_total_savings(db_path, member_id)
        if not ok:
            return False, "Failed to calculate total savings"

        max_allowed = loan_multiplier * total_savings
        if principal > max_allowed:
            return False, f"Loan exceeds {loan_multiplier}x savings limit (Max: ₦{max_allowed:,.2f})"

        # Insert loan with actual applied rate (audit trail)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute(
            """
            INSERT INTO Loans (member_id, principal, interest_rate, status, date_issued)
            VALUES (?, ?, ?, ?, ?)
            """,
            (member_id, principal, actual_interest_rate, 'Active', str(date.today())),
        )
        loan_id = cursor.lastrowid
        conn.commit()

        # Generate repayment schedule using applied rate and duration
        schedule_ok, schedule_msg = generate_repayment_schedule(
            db_path, loan_id, principal, actual_interest_rate, months=actual_duration
        )
        if not schedule_ok:
            conn.close()
            return True, f"Loan created (ID: {loan_id}) but schedule generation failed: {schedule_msg}"

        conn.close()
        return True, f"Loan created successfully (ID: {loan_id}) at {actual_interest_rate}% for {actual_duration} months"

    except sqlite3.IntegrityError as e:
        return False, f"Integrity error: {e}"
    except sqlite3.DatabaseError as e:
        return False, f"Database error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def get_member_loans(db_path: str, member_id: int) -> Tuple[bool, List[Dict]]:
    """
    Retrieve all loans for a member.

    Returns (True, loans_list) or (False, []).
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT loan_id, member_id, principal, interest_rate, status, date_issued, created_at
            FROM Loans
            WHERE member_id = ?
            ORDER BY date_issued DESC
            """,
            (member_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        loans = [dict(row) for row in rows]
        return True, loans

    except sqlite3.DatabaseError:
        return False, []
    except Exception:
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
