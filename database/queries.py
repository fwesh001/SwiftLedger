"""
Database query operations for SwiftLedger.
Handles CRUD operations for members, savings, loans, and repayment schedules.
"""

import sqlite3
from datetime import date, timedelta
from typing import Dict, List, Tuple, Optional

from database.db_init import log_event


def _safe_log_event(user: str, category: str, description: str, status: str, db_path: str) -> None:
    try:
        log_event(user=user, category=category, description=description, status=status, db_path=db_path)
    except Exception:
        pass


def add_member(db_path: str, member_data: Dict[str, str]) -> Tuple[bool, str]:
    """
    Add a new member to the members table.

    Args:
        db_path: Path to the SQLite database file.
        member_data: Dictionary containing:
            - 'staff_number': Unique staff ID (required)
            - 'full_name': Member's full name (required)
            - 'phone': Member's phone number (optional)
            - 'bank_name': Member's bank name (optional)
            - 'account_no': Member's account number (optional)
            - 'department': Member's department (optional)
            - 'date_joined': Member's date joined (YYYY-MM-DD, optional)
            - 'current_savings': Opening savings balance (optional)
            - 'total_loans': Opening loan balance (optional)

    Returns:
        A tuple (success: bool, message: str)
    """
    required_fields = ['staff_number', 'full_name']
    if not all(field in member_data for field in required_fields):
        missing = [f for f in required_fields if f not in member_data]
        _safe_log_event(
            user="Admin",
            category="Members",
            description=f"Member registration failed (missing: {', '.join(missing)})",
            status="Failed",
            db_path=db_path,
        )
        return False, f"Missing required fields: {', '.join(missing)}"

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA foreign_keys = ON;")
        conn.execute("BEGIN;")

        opening_savings = float(member_data.get('current_savings', 0.0) or 0.0)
        opening_loans = float(member_data.get('total_loans', 0.0) or 0.0)
        date_joined = member_data.get('date_joined') or date.today().isoformat()
        phone = member_data.get('phone') or '+234'
        bank_name = member_data.get('bank_name') or 'UBA'
        account_no = member_data.get('account_no') or ''
        department = member_data.get('department') or 'SLT'

        cursor.execute(
            """
            INSERT INTO members (
                staff_number, full_name, phone, bank_name, account_no, department, date_joined,
                current_savings, total_loans
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                member_data['staff_number'],
                member_data['full_name'],
                phone,
                bank_name,
                account_no,
                department,
                date_joined,
                opening_savings,
                opening_loans,
            ),
        )

        member_id = cursor.lastrowid

        if opening_savings > 0:
            cursor.execute(
                """
                INSERT INTO savings_transactions (member_id, trans_type, amount, running_balance)
                VALUES (?, ?, ?, ?)
                """,
                (member_id, 'Opening Balance', opening_savings, opening_savings),
            )

        if opening_loans > 0:
            settings_ok, settings = get_system_settings(db_path)
            interest_rate = 12.0
            duration_months = 24
            if settings_ok and settings:
                interest_rate = float(settings.get('default_interest_rate', interest_rate))
                duration_months = int(settings.get('default_duration', duration_months))

            due_date = (date.today() + timedelta(days=30 * duration_months)).isoformat()
            cursor.execute(
                """
                INSERT INTO loans (member_id, principal, interest_rate, duration_months, status, due_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (member_id, opening_loans, interest_rate, duration_months, 'Active', due_date),
            )

        conn.commit()

        _safe_log_event(
            user="Admin",
            category="Members",
            description=(
                f"Member registered: {member_data['full_name']} "
                f"({member_data['staff_number']}), ID {member_id}"
            ),
            status="Success",
            db_path=db_path,
        )

        return True, f"Member '{member_data['full_name']}' (Staff: {member_data['staff_number']}, ID: {member_id}) added successfully."

    except sqlite3.DatabaseError as e:
        if conn:
            conn.rollback()
        _safe_log_event(
            user="Admin",
            category="Members",
            description=f"Member registration failed (database error: {str(e)})",
            status="Failed",
            db_path=db_path,
        )
        return False, f"Database error: {str(e)}"

    except Exception as e:
        if conn:
            conn.rollback()
        _safe_log_event(
            user="Admin",
            category="Members",
            description=f"Member registration failed (unexpected error: {str(e)})",
            status="Failed",
            db_path=db_path,
        )
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
        Each member dict contains: member_id, staff_number, full_name, phone, bank_name,
        account_no, department, date_joined, current_savings, total_loans, default_loan_count,
        active_loan_count
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                m.member_id, m.staff_number, m.full_name, m.phone, m.bank_name,
                m.account_no, m.department, m.date_joined, m.avatar_path, m.current_savings, m.total_loans,
                (SELECT COUNT(1) FROM loans l WHERE l.member_id = m.member_id AND l.status = 'Default')
                    AS default_loan_count,
                (SELECT COUNT(1) FROM loans l WHERE l.member_id = m.member_id AND l.status = 'Active')
                    AS active_loan_count
            FROM members m
            ORDER BY m.member_id DESC
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


def delete_member(db_path: str, member_id: int) -> Tuple[bool, str]:
    """
    Delete a member and their related transactions/loans.

    Returns:
        (True, success_message) or (False, error_message)
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Fetch member info for audit
        cursor.execute("SELECT staff_number, full_name FROM members WHERE member_id = ?", (member_id,))
        row = cursor.fetchone()
        if not row:
            return False, f"Member ID {member_id} not found."
        staff_number, full_name = row

        # Delete related data
        cursor.execute("DELETE FROM savings_transactions WHERE member_id = ?", (member_id,))
        cursor.execute("DELETE FROM loans WHERE member_id = ?", (member_id,))
        cursor.execute("DELETE FROM members WHERE member_id = ?", (member_id,))

        conn.commit()

        _safe_log_event(
            user="Admin",
            category="Members",
            description=f"Member deleted: {full_name} ({staff_number}), ID {member_id}",
            status="Success",
            db_path=db_path,
        )

        return True, f"Member '{full_name}' ({staff_number}) has been deleted."

    except sqlite3.DatabaseError as e:
        if conn:
            conn.rollback()
        _safe_log_event("Admin", "Members",
                        f"Member deletion failed for ID {member_id} (DB error: {e})",
                        "Failed", db_path)
        return False, f"Database error: {e}"
    except Exception as e:
        if conn:
            conn.rollback()
        _safe_log_event("Admin", "Members",
                        f"Member deletion failed for ID {member_id} (error: {e})",
                        "Failed", db_path)
        return False, f"Unexpected error: {e}"
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
    defaults = {
        'min_monthly_saving': 0.0,
        'max_loan_amount': 0.0,
        'default_interest_rate': 12.0,
        'loan_multiplier': 2.0,
        'default_duration': 24,
        'show_charts': 0,
        'updated_at': None,
    }

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM system_settings ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()

        if not row:
            return True, defaults

        settings = defaults.copy()
        settings.update(dict(row))
        return True, settings

    except sqlite3.DatabaseError:
        return True, defaults
    except Exception:
        return True, defaults
    finally:
        if conn:
            conn.close()


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


def generate_repayment_schedule(
    db_path: str,
    loan_id: int,
    principal: float,
    interest_rate: float,
    months: int = 24,
) -> Tuple[bool, List[Dict]]:
    """
    Generate a repayment schedule for a loan without persisting to a table.
    """
    try:
        schedule = calculate_repayment_schedule(principal, interest_rate, months)
        return True, schedule
    except Exception as e:
        _safe_log_event(
            user="Admin",
            category="Loans",
            description=f"Failed to generate repayment schedule (error: {str(e)})",
            status="Failed",
            db_path=db_path,
        )
        return False, []


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
        _safe_log_event(
            user="Admin",
            category="Loans",
            description="Loan application failed (settings unavailable)",
            status="Failed",
            db_path=db_path,
        )
        return False, "Failed to retrieve system settings"

    loan_multiplier = float(settings.get('loan_multiplier', 2.0))

    ok, total_savings = get_total_savings(db_path, member_id)
    if not ok:
        _safe_log_event(
            user="Admin",
            category="Loans",
            description="Loan application failed (could not calculate savings)",
            status="Failed",
            db_path=db_path,
        )
        return False, "Failed to calculate total savings"

    max_allowed = loan_multiplier * total_savings
    if principal > max_allowed:
        _safe_log_event(
            user="Admin",
            category="Loans",
            description=(
                f"Loan application rejected for member_id {member_id} "
                f"(amount ₦{principal:,.2f} exceeds limit ₦{max_allowed:,.2f})"
            ),
            status="Failed",
            db_path=db_path,
        )
        return False, f"Loan exceeds {loan_multiplier}x savings limit (Max: ₦{max_allowed:,.2f})"

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        final_interest_rate = float(interest_rate) if interest_rate is not None else float(settings.get('default_interest_rate', 12.0))
        final_duration = int(duration) if duration is not None else int(settings.get('default_duration', 24))

        due_date = (date.today() + timedelta(days=30 * final_duration)).isoformat()
        cursor.execute(
            """
            INSERT INTO loans (member_id, principal, interest_rate, duration_months, status, due_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (member_id, principal, final_interest_rate, final_duration, 'Active', due_date),
        )

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
            _safe_log_event(
                user="Admin",
                category="Loans",
                description=f"Loan application failed (member_id {member_id} not found)",
                status="Failed",
                db_path=db_path,
            )
            return False, f"Error: Member ID {member_id} does not exist."

        conn.commit()
        _safe_log_event(
            user="Admin",
            category="Loans",
            description=(
                f"Loan approved for member_id {member_id}: ₦{principal:,.2f}, "
                f"{final_interest_rate:.2f}% for {final_duration} months"
            ),
            status="Success",
            db_path=db_path,
        )
        return True, f"Loan recorded successfully. Amount: ₦{principal:,.2f}"

    except sqlite3.DatabaseError as e:
        if conn:
            conn.rollback()
        _safe_log_event(
            user="Admin",
            category="Loans",
            description=f"Loan application failed (database error: {e})",
            status="Failed",
            db_path=db_path,
        )
        return False, f"Database error: {e}"
    except Exception as e:
        if conn:
            conn.rollback()
        _safe_log_event(
            user="Admin",
            category="Loans",
            description=f"Loan application failed (unexpected error: {e})",
            status="Failed",
            db_path=db_path,
        )
        return False, f"Unexpected error: {e}"

    finally:
        if conn:
            conn.close()


def get_member_loans(db_path: str, member_id: int) -> Tuple[bool, List[Dict]]:
    """
    Retrieve active loans for a member.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT loan_id, principal, interest_rate, status, date_issued
            FROM loans
            WHERE member_id = ?
            ORDER BY loan_id DESC
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


def check_overdue_loans(db_path: str) -> Tuple[bool, List[Dict]]:
    """
    Return overdue loans (due_date < today and not Paid).
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT l.loan_id, l.member_id, l.principal, l.due_date, l.status,
                   m.staff_number, m.full_name
            FROM loans l
            JOIN members m ON m.member_id = l.member_id
            WHERE l.due_date IS NOT NULL
              AND DATE(l.due_date) < DATE('now')
              AND l.status != 'Paid'
            ORDER BY l.due_date ASC
            """
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
                     SELECT member_id, staff_number, full_name, phone, bank_name, account_no,
                         department, date_joined, avatar_path, current_savings, total_loans
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
                     SELECT member_id, staff_number, full_name, phone, bank_name, account_no,
                         department, date_joined, avatar_path, current_savings, total_loans
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


def update_member_profile(db_path: str, member_id: int, updates: Dict[str, str]) -> Tuple[bool, str]:
    """
    Update editable member profile fields.

    Args:
        db_path: Path to the SQLite database file.
        member_id: The member's ID.
        updates: Dictionary of fields to update.

    Returns:
        A tuple (success: bool, message: str)
    """
    allowed = {"phone", "bank_name", "account_no", "department", "date_joined", "avatar_path"}
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return False, "No valid fields to update."

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        set_clause = ", ".join(f"{col} = ?" for col in filtered)
        values = list(filtered.values()) + [member_id]
        cursor.execute(
            f"UPDATE members SET {set_clause} WHERE member_id = ?",
            values,
        )

        if cursor.rowcount == 0:
            conn.rollback()
            return False, f"Member ID {member_id} not found."

        conn.commit()
        _safe_log_event(
            user="Admin",
            category="Members",
            description=f"Member profile updated for ID {member_id}",
            status="Success",
            db_path=db_path,
        )
        return True, "Member profile updated successfully."

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
        _safe_log_event(
            user="Admin",
            category="Savings",
            description=f"Savings transaction rejected (invalid category: {category})",
            status="Failed",
            db_path=db_path,
        )
        return False, f"Invalid category '{category}'. Must be 'Deduction' or 'Lodgment'."

    if amount <= 0:
        _safe_log_event(
            user="Admin",
            category="Savings",
            description="Savings transaction rejected (non-positive amount)",
            status="Failed",
            db_path=db_path,
        )
        return False, "Amount must be a positive number."

    if not isinstance(member_id, int) or member_id <= 0:
        _safe_log_event(
            user="Admin",
            category="Savings",
            description=f"Savings transaction rejected (invalid member_id: {member_id})",
            status="Failed",
            db_path=db_path,
        )
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
            _safe_log_event(
                user="Admin",
                category="Savings",
                description=f"Savings transaction failed (member_id {member_id} not found)",
                status="Failed",
                db_path=db_path,
            )
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
        _safe_log_event(
            user="Admin",
            category="Savings",
            description=(
                f"Savings {category} posted for member_id {member_id}: ₦{amount:,.2f}"
            ),
            status="Success",
            db_path=db_path,
        )
        return True, f"Savings updated successfully. Amount: {amount}, Category: {category}"

    except sqlite3.DatabaseError as e:
        if conn:
            conn.rollback()
        _safe_log_event(
            user="Admin",
            category="Savings",
            description=f"Savings transaction failed (database error: {str(e)})",
            status="Failed",
            db_path=db_path,
        )
        return False, f"Database error: {str(e)}"

    except Exception as e:
        if conn:
            conn.rollback()
        _safe_log_event(
            user="Admin",
            category="Savings",
            description=f"Savings transaction failed (unexpected error: {str(e)})",
            status="Failed",
            db_path=db_path,
        )
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


def get_all_logs(db_path: str) -> Tuple[bool, List[Dict]]:
    """
    Retrieve all audit log entries, newest first.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, timestamp, user, category, description, status
            FROM audit_logs
            ORDER BY id DESC
            """
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
