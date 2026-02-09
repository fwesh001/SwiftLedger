"""
Database query operations for SwiftLedger.
Handles CRUD operations for members, savings, loans, and repayment schedules.
"""

import sqlite3
from datetime import date
from typing import Dict, List, Tuple, Optional


def add_member(db_path: str, member_data: Dict[str, str]) -> Tuple[bool, str]:
    """
    Add a new member to the members table.

    Args:
        db_path: Path to the SQLite database file.
        member_data: Dictionary containing:
            - 'staff_number': Unique staff ID (required)
            - 'full_name': Member's full name (required)
            - 'phone': Member's phone number (optional)

    Returns:
        A tuple (success: bool, message: str)
    """
    required_fields = ['staff_number', 'full_name']
    if not all(field in member_data for field in required_fields):
        missing = [f for f in required_fields if f not in member_data]
        return False, f"Missing required fields: {', '.join(missing)}"

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA foreign_keys = ON;")

        cursor.execute(
            """
            INSERT INTO members (staff_number, full_name, phone, current_savings, total_loans)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                member_data['staff_number'],
                member_data['full_name'],
                member_data.get('phone', ''),
                float(member_data.get('current_savings', 0.0)),
                float(member_data.get('total_loans', 0.0)),
            ),
        )

        member_id = cursor.lastrowid
        conn.commit()

        return True, f"Member '{member_data['full_name']}' (Staff: {member_data['staff_number']}, ID: {member_id}) added successfully."

    except sqlite3.DatabaseError as e:
        if conn:
            conn.rollback()
        return False, f"Database error: {str(e)}"

    except Exception as e:
        if conn:
            conn.rollback()
        return False, f"Unexpected error: {str(e)}"

    finally:
        if conn:
            conn.close()


def get_all_members(db_path: str) -> Tuple[bool, List[Dict]]:
    """
    Retrieve all members from the members table.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A tuple (success: bool, members: List[Dict])
        Each member dict contains: member_id, staff_number, full_name, phone, current_savings, total_loans
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT member_id, staff_number, full_name, phone, current_savings, total_loans
            FROM members
            ORDER BY member_id DESC
            """
        )

        rows = cursor.fetchall()
        members = [dict(row) for row in rows]

        return True, members

    except sqlite3.DatabaseError:
        return False, []

    except Exception:
        return False, []

    finally:
        if conn:
            conn.close()


def get_total_savings(db_path: str, member_id: int) -> Tuple[bool, float]:
    """
    Retrieve current savings for a member.

    Returns (True, amount) on success or (False, 0.0) on error.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(current_savings, 0.0)
            FROM members
            WHERE member_id = ?
            """,
            (member_id,),
        )
        row = cursor.fetchone()
        total = float(row[0]) if row and row[0] is not None else 0.0
        return True, total

    except sqlite3.DatabaseError:
        return False, 0.0
    except Exception:
        return False, 0.0

    finally:
        if conn:
            conn.close()


def get_system_settings(db_path: str) -> Tuple[bool, Optional[Dict]]:
    """
    Retrieve system settings for loan defaults.

    The simplified schema does not store loan settings, so defaults are returned.
    """
    return True, {
        'min_monthly_saving': 0.0,
        'max_loan_amount': 0.0,
        'default_interest_rate': 12.0,
        'loan_multiplier': 2.0,
        'default_duration': 24,
        'updated_at': None,
    }


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
    conn = None
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
        return True, "Repayment schedule generated"

    except sqlite3.DatabaseError as e:
        if conn:
            conn.rollback()
        return False, f"Database error generating schedule: {e}"
    except Exception as e:
        if conn:
            conn.rollback()
        return False, f"Unexpected error generating schedule: {e}"
    
    finally:
        if conn:
            conn.close()


def apply_for_loan(
    db_path: str,
    member_id: int,
    principal: float,
    interest_rate: Optional[float] = None,
    duration: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Update a member's total_loans balance while enforcing a savings-multiplier rule.

    Args:
        db_path: Path to the SQLite database.
        member_id: The member applying for the loan.
        principal: Requested loan amount.
        interest_rate: Unused (kept for compatibility).
        duration: Unused (kept for compatibility).

    Returns:
        (True, success_message) on success or (False, error_message) on failure.
    """
    settings_ok, settings = get_system_settings(db_path)
    if not settings_ok or settings is None:
        return False, "Failed to retrieve system settings"

    loan_multiplier = float(settings.get('loan_multiplier', 2.0))

    ok, total_savings = get_total_savings(db_path, member_id)
    if not ok:
        return False, "Failed to calculate total savings"

    max_allowed = loan_multiplier * total_savings
    if principal > max_allowed:
        return False, f"Loan exceeds {loan_multiplier}x savings limit (Max: ₦{max_allowed:,.2f})"

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE members
            SET total_loans = COALESCE(total_loans, 0.0) + ?
            WHERE member_id = ?
            """,
            (principal, member_id),
        )

        if cursor.rowcount == 0:
            conn.rollback()
            return False, f"Error: Member ID {member_id} does not exist."

        conn.commit()
        return True, f"Loan recorded successfully. Amount: ₦{principal:,.2f}"

    except sqlite3.DatabaseError as e:
        if conn:
            conn.rollback()
        return False, f"Database error: {e}"
    except Exception as e:
        if conn:
            conn.rollback()
        return False, f"Unexpected error: {e}"

    finally:
        if conn:
            conn.close()


def get_member_loans(db_path: str, member_id: int) -> Tuple[bool, List[Dict]]:
    """
    Return an empty list for loans history in the simplified schema.
    """
    return True, []



def get_member_by_id(db_path: str, member_id: int) -> Tuple[bool, Optional[Dict]]:
    """
    Retrieve a specific member by ID.
    
    Args:
        db_path: Path to the SQLite database file.
        member_id: The member's ID.
    
    Returns:
        A tuple (success: bool, member: Optional[Dict])
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT member_id, staff_number, full_name, phone, current_savings, total_loans
            FROM members
            WHERE member_id = ?
            """,
            (member_id,),
        )
        
        row = cursor.fetchone()
        
        if row:
            return True, dict(row)
        else:
            return False, None
    
    except Exception as e:
        return False, None
    
    finally:
        if conn:
            conn.close()


def get_member_by_staff_number(db_path: str, staff_number: str) -> Tuple[bool, Optional[Dict]]:
    """
    Retrieve a specific member by staff number.

    Args:
        db_path: Path to the SQLite database file.
        staff_number: The member's staff number.

    Returns:
        A tuple (success: bool, member: Optional[Dict])
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT member_id, staff_number, full_name, phone, current_savings, total_loans
            FROM members
            WHERE staff_number = ?
            """,
            (staff_number,),
        )

        row = cursor.fetchone()

        if row:
            return True, dict(row)
        return False, None

    except Exception:
        return False, None

    finally:
        if conn:
            conn.close()


def add_saving(db_path: str, member_id: int, amount: float, category: str) -> Tuple[bool, str]:
    """
    Update a member's current savings balance.

    Args:
        db_path: Path to the SQLite database file.
        member_id: The ID of the member.
        amount: The savings amount (positive number).
        category: Either 'Deduction' or 'Lodgment'.

    Returns:
        A tuple (success: bool, message: str)
    """
    if category not in ['Deduction', 'Lodgment']:
        return False, f"Invalid category '{category}'. Must be 'Deduction' or 'Lodgment'."

    if amount <= 0:
        return False, "Amount must be a positive number."

    if not isinstance(member_id, int) or member_id <= 0:
        return False, "Invalid member ID."

    delta = amount if category == 'Lodgment' else -amount

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE members
            SET current_savings = COALESCE(current_savings, 0.0) + ?
            WHERE member_id = ?
            """,
            (delta, member_id),
        )

        if cursor.rowcount == 0:
            conn.rollback()
            return False, f"Error: Member ID {member_id} does not exist."

        cursor.execute(
            """
            SELECT COALESCE(current_savings, 0.0)
            FROM members
            WHERE member_id = ?
            """,
            (member_id,),
        )
        row = cursor.fetchone()
        running_balance = float(row[0]) if row and row[0] is not None else 0.0

        cursor.execute(
            """
            INSERT INTO savings_transactions (member_id, trans_type, amount, running_balance)
            VALUES (?, ?, ?, ?)
            """,
            (member_id, category, amount, running_balance),
        )

        conn.commit()
        return True, f"Savings updated successfully. Amount: {amount}, Category: {category}"

    except sqlite3.DatabaseError as e:
        if conn:
            conn.rollback()
        return False, f"Database error: {str(e)}"

    except Exception as e:
        if conn:
            conn.rollback()
        return False, f"Unexpected error: {str(e)}"

    finally:
        if conn:
            conn.close()


def get_member_savings(db_path: str, member_id: int) -> Tuple[bool, List[Dict]]:
    """
    Retrieve the last 10 savings transactions for a member.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, trans_date, trans_type, amount, running_balance
            FROM savings_transactions
            WHERE member_id = ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (member_id,),
        )

        rows = cursor.fetchall()
        return True, [dict(row) for row in rows]

    except sqlite3.DatabaseError:
        return False, []
    except Exception:
        return False, []
    finally:
        if conn:
            conn.close()


def get_society_stats(db_path: str) -> Tuple[bool, Dict]:
    """
    Calculate comprehensive financial statistics for the society.
    
    Returns a dictionary containing:
    - total_members: Count of all members
    - total_savings: Sum of all current_savings
    - total_loans_disbursed: Sum of all total_loans
    - total_projected_interest: Calculated interest (total_loans * interest_rate)
    - members_dividend_share: 60% of projected interest
    - society_dividend_share: 40% of projected interest
    
    Args:
        db_path: Path to the SQLite database file.
    
    Returns:
        A tuple (success: bool, stats: Dict)
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # 1. Total Members (count of all members)
        cursor.execute("SELECT COUNT(*) FROM members")
        total_members = cursor.fetchone()[0] or 0
        
        # 2. Total Savings (sum of current_savings from all members)
        cursor.execute("""
            SELECT COALESCE(SUM(current_savings), 0.0)
            FROM members
        """)
        total_savings = float(cursor.fetchone()[0] or 0.0)
        
        # 3. Total Loans Disbursed (sum of total_loans from all members)
        cursor.execute("""
            SELECT COALESCE(SUM(total_loans), 0.0)
            FROM members
        """)
        total_loans_disbursed = float(cursor.fetchone()[0] or 0.0)
        
        # 4. Total Projected Interest (estimate: 12% of total loans by default)
        # This is a simplified calculation; in production this would come from loan records
        total_projected_interest = round(total_loans_disbursed * 0.12, 2)
        
        # 5. Calculate dividend shares
        members_dividend_share = round(total_projected_interest * 0.60, 2)
        society_dividend_share = round(total_projected_interest * 0.40, 2)
        
        # Compile statistics dictionary
        stats = {
            'total_members': total_members,
            'total_savings': round(total_savings, 2),
            'total_loans_disbursed': round(total_loans_disbursed, 2),
            'total_projected_interest': total_projected_interest,
            'members_dividend_share': members_dividend_share,
            'society_dividend_share': society_dividend_share,
        }
        
        return True, stats
    
    except sqlite3.DatabaseError as e:
        return False, {}
    
    except Exception as e:
        return False, {}
    
    finally:
        if conn:
            conn.close()


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
