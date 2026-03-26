"""
Database query operations for SwiftLedger.
Handles CRUD operations for members, savings, loans, and repayment schedules.
"""

import sqlite3
from datetime import date, datetime, timedelta
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
        trans_date = member_data.get('trans_date') or date_joined
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
                INSERT INTO savings_transactions (
                    member_id, trans_date, trans_type, amount, running_balance, payment_mode
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    member_id,
                    trans_date,
                    'Opening Balance',
                    opening_savings,
                    opening_savings,
                    'Salary Deduction',
                ),
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
                INSERT INTO loans (member_id, principal, interest_rate, duration_months, status, due_date, date_issued)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (member_id, opening_loans, interest_rate, duration_months, 'Active', due_date, trans_date),
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
                m.account_no, m.department, m.date_joined, m.avatar_path,
                (
                    SELECT COALESCE(SUM(
                        CASE
                            WHEN st.trans_type IN ('Lodgment', 'Opening Balance') THEN st.amount
                            WHEN st.trans_type = 'Deduction' THEN -st.amount
                            ELSE 0
                        END
                    ), 0)
                    FROM savings_transactions st
                    WHERE st.member_id = m.member_id
                ) AS current_savings,
                m.total_loans,
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


def search_members(db_path: str, query: str, filter_field: str = "all") -> Tuple[bool, List[Dict]]:
    """
    Search for members by staff number, name, or phone (case-insensitive, partial match).

    Args:
        db_path: Path to the SQLite database file.
        query: Search term (will match against selected field(s)).
        filter_field: Which field to search: 'all' (default), 'staff_number', 'full_name', or 'phone'.

    Returns:
        A tuple (success: bool, members: List[Dict])
        Each member dict contains the same fields as get_all_members.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        search_term = f"%{query}%"
        
        # Build WHERE clause based on filter_field
        if filter_field == "staff_number":
            where_clause = "LOWER(m.staff_number) LIKE LOWER(?)"
            params = (search_term,)
        elif filter_field == "full_name":
            where_clause = "LOWER(m.full_name) LIKE LOWER(?)"
            params = (search_term,)
        elif filter_field == "phone":
            where_clause = "LOWER(m.phone) LIKE LOWER(?)"
            params = (search_term,)
        else:  # "all" or any other value
            where_clause = """
                LOWER(m.staff_number) LIKE LOWER(?)
                OR LOWER(m.full_name) LIKE LOWER(?)
                OR LOWER(m.phone) LIKE LOWER(?)
            """
            params = (search_term, search_term, search_term)
        
        cursor.execute(
            f"""
            SELECT
                m.member_id, m.staff_number, m.full_name, m.phone, m.bank_name,
                m.account_no, m.department, m.date_joined, m.avatar_path,
                (
                    SELECT COALESCE(SUM(
                        CASE
                            WHEN st.trans_type IN ('Lodgment', 'Opening Balance') THEN st.amount
                            WHEN st.trans_type = 'Deduction' THEN -st.amount
                            ELSE 0
                        END
                    ), 0)
                    FROM savings_transactions st
                    WHERE st.member_id = m.member_id
                ) AS current_savings,
                m.total_loans,
                (SELECT COUNT(1) FROM loans l WHERE l.member_id = m.member_id AND l.status = 'Default')
                    AS default_loan_count,
                (SELECT COUNT(1) FROM loans l WHERE l.member_id = m.member_id AND l.status = 'Active')
                    AS active_loan_count
            FROM members m
            WHERE {where_clause}
            ORDER BY m.member_id DESC
            """,
            params,
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

        # Delete related data in FK-safe order
        cursor.execute("DELETE FROM loan_repayments WHERE member_id = ?", (member_id,))
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


def delete_all_members(db_path: str) -> Tuple[bool, str]:
    """Delete all members and linked financial records in a single transaction."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        conn.execute("BEGIN;")

        cursor.execute("SELECT COUNT(1) FROM members")
        member_count = int(cursor.fetchone()[0] or 0)
        if member_count == 0:
            return True, "No members to delete."

        cursor.execute("SELECT COUNT(1) FROM savings_transactions")
        savings_count = int(cursor.fetchone()[0] or 0)
        cursor.execute("SELECT COUNT(1) FROM loan_repayments")
        repayment_count = int(cursor.fetchone()[0] or 0)
        cursor.execute("SELECT COUNT(1) FROM loans")
        loan_count = int(cursor.fetchone()[0] or 0)

        cursor.execute("DELETE FROM loan_repayments")
        cursor.execute("DELETE FROM savings_transactions")
        cursor.execute("DELETE FROM loans")
        cursor.execute("DELETE FROM members")

        conn.commit()

        _safe_log_event(
            user="Admin",
            category="Members",
            description=(
                "Delete all members completed "
                f"(members={member_count}, loans={loan_count}, repayments={repayment_count}, savings={savings_count})"
            ),
            status="Success",
            db_path=db_path,
        )
        return True, (
            "Deleted all members and linked records "
            f"(Members: {member_count}, Loans: {loan_count}, Repayments: {repayment_count}, Savings: {savings_count})."
        )
    except sqlite3.DatabaseError as e:
        if conn:
            conn.rollback()
        _safe_log_event(
            user="Admin",
            category="Members",
            description=f"Delete all members failed (DB error: {e})",
            status="Failed",
            db_path=db_path,
        )
        return False, f"Database error: {e}"
    except Exception as e:
        if conn:
            conn.rollback()
        _safe_log_event(
            user="Admin",
            category="Members",
            description=f"Delete all members failed (error: {e})",
            status="Failed",
            db_path=db_path,
        )
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
            SELECT COALESCE(SUM(
                CASE
                    WHEN trans_type IN ('Lodgment', 'Opening Balance') THEN amount
                    WHEN trans_type = 'Deduction' THEN -amount
                    ELSE 0
                END
            ), 0.0)
            FROM savings_transactions
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
        'society_name': 'SwiftLedger',
        'address': '',
        'street': '',
        'city_state': '',
        'phone': '',
        'email': '',
        'min_monthly_saving': 0.0,
        'default_interest_rate': 12.0,
        'loan_multiplier': 2.0,
        'default_duration': 24,
        'show_charts': 0,
        'show_alerts': 1,
        'theme': 'dark',
        'text_scale': 1.0,
        'timeout_minutes': 10,
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
        settings['address'] = settings.get('address') or settings.get('street') or ''
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


def get_loan_products(db_path: str, active_only: bool = True) -> Tuple[bool, List[Dict]]:
    """Retrieve configured loan products."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if active_only:
            cursor.execute(
                """
                SELECT product_id, name, max_amount, interest_rate, duration_months, is_active
                FROM loan_products
                WHERE is_active = 1
                ORDER BY name ASC
                """
            )
        else:
            cursor.execute(
                """
                SELECT product_id, name, max_amount, interest_rate, duration_months, is_active
                FROM loan_products
                ORDER BY is_active DESC, name ASC
                """
            )
        rows = cursor.fetchall()
        return True, [dict(row) for row in rows]
    except Exception:
        return False, []
    finally:
        if conn:
            conn.close()


def add_loan_product(
    db_path: str,
    name: str,
    max_amount: float,
    interest_rate: float,
    duration_months: int,
) -> Tuple[bool, str]:
    """Create a reusable loan product definition."""
    if not name.strip():
        return False, "Product name is required."
    if max_amount < 0:
        return False, "Max amount cannot be negative."
    if interest_rate < 0:
        return False, "Interest rate cannot be negative."
    if duration_months <= 0:
        return False, "Duration must be at least 1 month."

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO loan_products (name, max_amount, interest_rate, duration_months, is_active, updated_at)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """,
            (name.strip(), float(max_amount), float(interest_rate), int(duration_months)),
        )
        conn.commit()
        _safe_log_event(
            user="Admin",
            category="Loans",
            description=(
                f"Loan product created: {name.strip()} "
                f"(max ₦{max_amount:,.2f}, {interest_rate:.2f}%/{duration_months}m)"
            ),
            status="Success",
            db_path=db_path,
        )
        return True, "Loan product created successfully."
    except sqlite3.IntegrityError:
        return False, "A loan product with this name already exists."
    except Exception as e:
        if conn:
            conn.rollback()
        return False, f"Failed to create product: {e}"
    finally:
        if conn:
            conn.close()


def update_loan_product(
    db_path: str,
    product_id: int,
    name: str,
    max_amount: float,
    interest_rate: float,
    duration_months: int,
) -> Tuple[bool, str]:
    """Update an existing loan product definition."""
    if product_id <= 0:
        return False, "Invalid product ID."
    if not name.strip():
        return False, "Product name is required."
    if max_amount < 0:
        return False, "Max amount cannot be negative."
    if interest_rate < 0:
        return False, "Interest rate cannot be negative."
    if duration_months <= 0:
        return False, "Duration must be at least 1 month."

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE loan_products
            SET name = ?,
                max_amount = ?,
                interest_rate = ?,
                duration_months = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE product_id = ?
            """,
            (name.strip(), float(max_amount), float(interest_rate), int(duration_months), int(product_id)),
        )
        if cursor.rowcount == 0:
            conn.rollback()
            return False, "Loan product not found."

        conn.commit()
        _safe_log_event(
            user="Admin",
            category="Loans",
            description=(
                f"Loan product updated: {name.strip()} "
                f"(max ₦{max_amount:,.2f}, {interest_rate:.2f}%/{duration_months}m)"
            ),
            status="Success",
            db_path=db_path,
        )
        return True, "Loan product updated successfully."
    except sqlite3.IntegrityError:
        return False, "A loan product with this name already exists."
    except Exception as e:
        if conn:
            conn.rollback()
        return False, f"Failed to update product: {e}"
    finally:
        if conn:
            conn.close()


def set_loan_product_active(
    db_path: str,
    product_id: int,
    is_active: bool,
) -> Tuple[bool, str]:
    """Activate or deactivate a loan product."""
    if product_id <= 0:
        return False, "Invalid product ID."

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE loan_products
            SET is_active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE product_id = ?
            """,
            (1 if is_active else 0, int(product_id)),
        )
        if cursor.rowcount == 0:
            conn.rollback()
            return False, "Loan product not found."

        conn.commit()
        _safe_log_event(
            user="Admin",
            category="Loans",
            description=f"Loan product {'activated' if is_active else 'deactivated'} (id={product_id})",
            status="Success",
            db_path=db_path,
        )
        return True, f"Loan product {'activated' if is_active else 'deactivated'} successfully."
    except Exception as e:
        if conn:
            conn.rollback()
        return False, f"Failed to update product status: {e}"
    finally:
        if conn:
            conn.close()


def _persist_repayment_schedule(
    cursor: sqlite3.Cursor,
    loan_id: int,
    member_id: int,
    principal: float,
    interest_rate: float,
    duration_months: int,
    issued_date: Optional[str] = None,
) -> None:
    """Persist generated repayment schedule rows for a loan."""
    schedule = calculate_repayment_schedule(principal, interest_rate, duration_months)
    base_date = date.today()
    if issued_date:
        try:
            base_date = date.fromisoformat(str(issued_date)[:10])
        except ValueError:
            base_date = date.today()

    for month_data in schedule:
        due = (base_date + timedelta(days=30 * int(month_data['month_number']))).isoformat()
        cursor.execute(
            """
            INSERT INTO loan_repayments (
                loan_id, member_id, installment_no, due_date,
                principal_due, interest_due, total_due,
                principal_paid, interest_paid, total_paid, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, 0.0, 'Pending')
            """,
            (
                loan_id,
                member_id,
                int(month_data['month_number']),
                due,
                float(month_data['principal_payment']),
                float(month_data['interest_payment']),
                float(month_data['total_payment']),
            ),
        )


def _backfill_missing_repayment_schedules(
    cursor: sqlite3.Cursor,
    member_id: int,
) -> int:
    """Create repayment schedules for active loans that have none (legacy data fix)."""
    cursor.execute(
        """
        SELECT
            l.loan_id,
            l.principal,
            l.interest_rate,
            l.duration_months,
            l.date_issued
        FROM loans l
        WHERE l.member_id = ?
          AND l.status IN ('Active', 'Overdue', 'Default')
          AND MAX(0, l.principal - COALESCE(l.principal_paid, 0.0)) > 0
          AND NOT EXISTS (
              SELECT 1
              FROM loan_repayments lr
              WHERE lr.loan_id = l.loan_id
          )
        ORDER BY l.loan_id ASC
        """,
        (member_id,),
    )
    missing_loans = cursor.fetchall()
    created_count = 0

    for loan_row in missing_loans:
        loan_id = int(loan_row[0])
        principal = float(loan_row[1] or 0.0)
        interest_rate = float(loan_row[2] or 0.0)
        duration_months = int(loan_row[3] or 0)
        date_issued = loan_row[4]

        if principal <= 0 or duration_months <= 0:
            continue

        _persist_repayment_schedule(
            cursor=cursor,
            loan_id=loan_id,
            member_id=member_id,
            principal=principal,
            interest_rate=interest_rate,
            duration_months=duration_months,
            issued_date=str(date_issued) if date_issued else None,
        )
        created_count += 1

    return created_count


def apply_for_loan(
    db_path: str,
    member_id: int,
    principal: float,
    interest_rate: Optional[float] = None,
    duration: Optional[int] = None,
    product_id: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    Update a member's total_loans balance while enforcing a savings-multiplier rule.

    Args:
        db_path: Path to the SQLite database.
        member_id: The member applying for the loan.
        principal: Requested loan amount.
        interest_rate: Optional annual interest override.
        duration: Optional duration override (months).
        product_id: Optional selected loan product ID.

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
    min_monthly_saving = float(settings.get('min_monthly_saving', 0.0))

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

    if min_monthly_saving > 0 and total_savings < min_monthly_saving:
        return False, (
            f"Member savings (₦{total_savings:,.2f}) is below the minimum threshold "
            f"(₦{min_monthly_saving:,.2f})."
        )

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
        conn.execute("BEGIN;")

        selected_product = None
        if product_id:
            cursor.execute(
                """
                SELECT product_id, name, max_amount, interest_rate, duration_months, is_active
                FROM loan_products
                WHERE product_id = ?
                """,
                (product_id,),
            )
            row = cursor.fetchone()
            if not row:
                conn.rollback()
                return False, "Selected loan product was not found."
            selected_product = {
                'product_id': row[0],
                'name': row[1],
                'max_amount': float(row[2] or 0.0),
                'interest_rate': float(row[3] or 0.0),
                'duration_months': int(row[4] or 0),
                'is_active': int(row[5] or 0),
            }
            if selected_product['is_active'] != 1:
                conn.rollback()
                return False, "Selected loan product is inactive."
            if selected_product['max_amount'] > 0 and principal > selected_product['max_amount']:
                conn.rollback()
                return False, (
                    f"Loan exceeds product cap (Max: ₦{selected_product['max_amount']:,.2f})."
                )

        if selected_product and interest_rate is None:
            final_interest_rate = selected_product['interest_rate']
        else:
            final_interest_rate = float(interest_rate) if interest_rate is not None else float(settings.get('default_interest_rate', 12.0))

        if selected_product and duration is None:
            final_duration = selected_product['duration_months']
        else:
            final_duration = int(duration) if duration is not None else int(settings.get('default_duration', 24))

        if final_duration <= 0:
            conn.rollback()
            return False, "Loan duration must be at least 1 month."

        due_date = (date.today() + timedelta(days=30 * final_duration)).isoformat()
        cursor.execute(
            """
            INSERT INTO loans (
                member_id, principal, interest_rate, duration_months, product_id,
                principal_paid, interest_paid, total_repaid, status, due_date
            )
            VALUES (?, ?, ?, ?, ?, 0.0, 0.0, 0.0, ?, ?)
            """,
            (
                member_id,
                principal,
                final_interest_rate,
                final_duration,
                selected_product['product_id'] if selected_product else None,
                'Active',
                due_date,
            ),
        )
        loan_id = int(cursor.lastrowid)

        _persist_repayment_schedule(
            cursor=cursor,
            loan_id=loan_id,
            member_id=member_id,
            principal=principal,
            interest_rate=final_interest_rate,
            duration_months=final_duration,
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
        product_note = ""
        if selected_product:
            product_note = f" ({selected_product['name']})"
        _safe_log_event(
            user="Admin",
            category="Loans",
            description=(
                f"Loan approved for member_id {member_id}{product_note}: ₦{principal:,.2f}, "
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
            SELECT
                l.loan_id,
                l.principal,
                l.interest_rate,
                l.duration_months,
                l.status,
                l.date_issued,
                l.principal_paid,
                l.interest_paid,
                l.total_repaid,
                l.product_id,
                lp.name AS product_name,
                MAX(0, l.principal - COALESCE(l.principal_paid, 0.0)) AS outstanding_principal
            FROM loans l
            LEFT JOIN loan_products lp ON lp.product_id = l.product_id
            WHERE l.member_id = ?
            ORDER BY l.loan_id DESC
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


def add_saving(
    db_path: str,
    member_id: int,
    amount: float,
    category: str,
    payment_mode: str = "Cash",
    transfer_reference: str = "",
) -> Tuple[bool, str]:
    """
    Update a member's current savings balance.

    Args:
        db_path: Path to the SQLite database file.
        member_id: The ID of the member.
        amount: The savings amount (positive number).
        category: Either 'Deduction' or 'Lodgment'.
        payment_mode: 'Bank Transfer', 'Cash', or 'Salary Deduction'.
        transfer_reference: Optional bank transfer reference ID.

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

    valid_payment_modes = ["Bank Transfer", "Cash", "Salary Deduction"]
    if payment_mode not in valid_payment_modes:
        _safe_log_event(
            user="Admin",
            category="Savings",
            description=f"Savings transaction rejected (invalid payment mode: {payment_mode})",
            status="Failed",
            db_path=db_path,
        )
        return False, "Invalid payment mode."

    transfer_reference = (transfer_reference or "").strip()

    if payment_mode == "Salary Deduction" and category != "Lodgment":
        _safe_log_event(
            user="Admin",
            category="Savings",
            description="Savings transaction rejected (salary deduction with withdrawal)",
            status="Failed",
            db_path=db_path,
        )
        return False, "Salary Deduction must be a deposit."

    if not isinstance(member_id, int) or member_id <= 0:
        _safe_log_event(
            user="Admin",
            category="Savings",
            description=f"Savings transaction rejected (invalid member_id: {member_id})",
            status="Failed",
            db_path=db_path,
        )
        return False, "Invalid member ID."

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
        if not row:
            _safe_log_event(
                user="Admin",
                category="Savings",
                description=f"Savings transaction failed (member_id {member_id} not found)",
                status="Failed",
                db_path=db_path,
            )
            return False, f"Error: Member ID {member_id} does not exist."

        current_savings = float(row[0] or 0.0)
        if category == "Deduction" and amount > current_savings:
            _safe_log_event(
                user="Admin",
                category="Savings",
                description=(
                    f"Savings withdrawal rejected (insufficient funds for member_id {member_id})"
                ),
                status="Failed",
                db_path=db_path,
            )
            return False, "Withdrawal exceeds current savings balance."

        delta = amount if category == "Lodgment" else -amount

        cursor.execute(
            """
            UPDATE members
            SET current_savings = COALESCE(current_savings, 0.0) + ?
            WHERE member_id = ?
            """,
            (delta, member_id),
        )

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
            INSERT INTO savings_transactions (
                member_id, trans_type, amount, running_balance, payment_mode, transfer_reference
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (member_id, category, amount, running_balance, payment_mode, transfer_reference),
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


def get_member_loan_totals(db_path: str, member_id: int) -> Tuple[bool, Dict[str, float]]:
    """Return total issued, repaid and outstanding principal for a member's loans."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(principal), 0.0) AS total_issued,
                COALESCE(SUM(total_repaid), 0.0) AS total_repaid,
                COALESCE(SUM(MAX(0, principal - COALESCE(principal_paid, 0.0))), 0.0) AS outstanding_principal
            FROM loans
            WHERE member_id = ?
            """,
            (member_id,),
        )
        row = cursor.fetchone() or (0.0, 0.0, 0.0)
        return True, {
            "total_issued": float(row[0] or 0.0),
            "total_repaid": float(row[1] or 0.0),
            "outstanding_principal": float(row[2] or 0.0),
        }
    except Exception:
        return False, {"total_issued": 0.0, "total_repaid": 0.0, "outstanding_principal": 0.0}
    finally:
        if conn:
            conn.close()


def has_active_loans(db_path: str, member_id: int) -> bool:
    """Return True if member currently has at least one active/defaulted/overdue loan."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 1
            FROM loans
            WHERE member_id = ?
              AND status IN ('Active', 'Overdue', 'Default')
              AND MAX(0, principal - COALESCE(principal_paid, 0.0)) > 0
            LIMIT 1
            """,
            (member_id,),
        )
        return cursor.fetchone() is not None
    except Exception:
        return False
    finally:
        if conn:
            conn.close()


def post_loan_repayment(
    db_path: str,
    member_id: int,
    amount: float,
    payment_mode: str = "Cash",
    transfer_reference: str = "",
) -> Tuple[bool, str]:
    """Apply repayment amount against pending installments for active loans."""
    if amount <= 0:
        return False, "Repayment amount must be greater than 0."

    transfer_reference = (transfer_reference or "").strip()
    valid_payment_modes = ["Bank Transfer", "Cash", "Salary Deduction"]
    if payment_mode not in valid_payment_modes:
        return False, "Invalid payment mode."

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        conn.execute("BEGIN;")

        cursor.execute(
            "SELECT COALESCE(current_savings, 0.0) FROM members WHERE member_id = ?",
            (member_id,),
        )
        mrow = cursor.fetchone()
        if not mrow:
            conn.rollback()
            return False, f"Error: Member ID {member_id} does not exist."
        current_savings = float(mrow[0] or 0.0)

        cursor.execute(
            """
            SELECT
                lr.repayment_id,
                lr.loan_id,
                lr.principal_due,
                lr.interest_due,
                lr.principal_paid,
                lr.interest_paid,
                lr.total_due,
                lr.total_paid
            FROM loan_repayments lr
            JOIN loans l ON l.loan_id = lr.loan_id
            WHERE lr.member_id = ?
              AND l.status IN ('Active', 'Overdue', 'Default')
              AND lr.status IN ('Pending', 'Partial')
            ORDER BY DATE(COALESCE(lr.due_date, l.date_issued)) ASC, lr.installment_no ASC
            """,
            (member_id,),
        )
        installments = cursor.fetchall()

        if not installments:
            created = _backfill_missing_repayment_schedules(cursor, member_id)
            if created > 0:
                cursor.execute(
                    """
                    SELECT
                        lr.repayment_id,
                        lr.loan_id,
                        lr.principal_due,
                        lr.interest_due,
                        lr.principal_paid,
                        lr.interest_paid,
                        lr.total_due,
                        lr.total_paid
                    FROM loan_repayments lr
                    JOIN loans l ON l.loan_id = lr.loan_id
                    WHERE lr.member_id = ?
                      AND l.status IN ('Active', 'Overdue', 'Default')
                      AND lr.status IN ('Pending', 'Partial')
                    ORDER BY DATE(COALESCE(lr.due_date, l.date_issued)) ASC, lr.installment_no ASC
                    """,
                    (member_id,),
                )
                installments = cursor.fetchall()

        if not installments:
            conn.rollback()
            return False, "No pending loan repayments found for this member."

        remaining = float(amount)
        principal_component = 0.0
        interest_component = 0.0

        for row in installments:
            if remaining <= 0:
                break
            repayment_id, loan_id, principal_due, interest_due, principal_paid, interest_paid, total_due, total_paid = row

            principal_due = float(principal_due or 0.0)
            interest_due = float(interest_due or 0.0)
            principal_paid = float(principal_paid or 0.0)
            interest_paid = float(interest_paid or 0.0)
            total_due = float(total_due or 0.0)
            total_paid = float(total_paid or 0.0)

            remaining_interest = max(0.0, interest_due - interest_paid)
            remaining_principal = max(0.0, principal_due - principal_paid)
            remaining_installment = max(0.0, total_due - total_paid)
            if remaining_installment <= 0:
                continue

            to_apply = min(remaining, remaining_installment)
            applied_interest = min(to_apply, remaining_interest)
            applied_principal = min(to_apply - applied_interest, remaining_principal)

            new_interest_paid = interest_paid + applied_interest
            new_principal_paid = principal_paid + applied_principal
            new_total_paid = total_paid + to_apply
            status = "Paid" if new_total_paid + 0.005 >= total_due else "Partial"

            cursor.execute(
                """
                UPDATE loan_repayments
                SET principal_paid = ?,
                    interest_paid = ?,
                    total_paid = ?,
                    status = ?,
                    payment_date = CASE WHEN ? = 'Paid' THEN CURRENT_TIMESTAMP ELSE payment_date END
                WHERE repayment_id = ?
                """,
                (new_principal_paid, new_interest_paid, new_total_paid, status, status, repayment_id),
            )

            cursor.execute(
                """
                UPDATE loans
                SET principal_paid = COALESCE(principal_paid, 0.0) + ?,
                    interest_paid = COALESCE(interest_paid, 0.0) + ?,
                    total_repaid = COALESCE(total_repaid, 0.0) + ?
                WHERE loan_id = ?
                """,
                (applied_principal, applied_interest, to_apply, loan_id),
            )

            principal_component += applied_principal
            interest_component += applied_interest
            remaining -= to_apply

        applied_total = round(amount - remaining, 2)
        if applied_total <= 0:
            conn.rollback()
            return False, "Repayment could not be applied."

        cursor.execute(
            """
            UPDATE loans
            SET status = CASE
                WHEN principal_paid >= principal THEN 'Paid'
                ELSE status
            END
            WHERE member_id = ?
            """,
            (member_id,),
        )

        cursor.execute(
            """
            UPDATE members
            SET total_loans = (
                SELECT COALESCE(SUM(MAX(0, principal - COALESCE(principal_paid, 0.0))), 0.0)
                FROM loans
                WHERE member_id = ?
            )
            WHERE member_id = ?
            """,
            (member_id, member_id),
        )

        cursor.execute(
            """
            INSERT INTO savings_transactions (
                member_id, trans_type, amount, running_balance, payment_mode, transfer_reference
            )
            VALUES (?, 'Loan Repayment', ?, ?, ?, ?)
            """,
            (member_id, applied_total, current_savings, payment_mode, transfer_reference),
        )

        conn.commit()
        _safe_log_event(
            user="Admin",
            category="Loans",
            description=(
                f"Loan repayment posted for member_id {member_id}: ₦{applied_total:,.2f} "
                f"(principal ₦{principal_component:,.2f}, interest ₦{interest_component:,.2f})"
            ),
            status="Success",
            db_path=db_path,
        )
        return True, f"Loan repayment posted successfully. Amount applied: ₦{applied_total:,.2f}"

    except Exception as e:
        if conn:
            conn.rollback()
        _safe_log_event(
            user="Admin",
            category="Loans",
            description=f"Loan repayment failed for member_id {member_id} (error: {e})",
            status="Failed",
            db_path=db_path,
        )
        return False, f"Failed to post repayment: {e}"
    finally:
        if conn:
            conn.close()


def get_member_loan_repayments(
    db_path: str,
    member_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tuple[bool, List[Dict]]:
    """Return repayment rows for a member with optional date filters."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = (
            """
            SELECT repayment_id, loan_id, installment_no, due_date,
                   principal_due, interest_due, total_due,
                   principal_paid, interest_paid, total_paid, status, payment_date
            FROM loan_repayments
            WHERE member_id = ?
            """
        )
        params: List[object] = [member_id]
        if start_date:
            query += " AND DATE(COALESCE(payment_date, due_date)) >= DATE(?)"
            params.append(start_date)
        if end_date:
            query += " AND DATE(COALESCE(payment_date, due_date)) <= DATE(?)"
            params.append(end_date)
        query += " ORDER BY repayment_id DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return True, [dict(row) for row in rows]
    except Exception:
        return False, []
    finally:
        if conn:
            conn.close()


def get_repayment_dashboard_rows(
    db_path: str,
    member_id: Optional[int] = None,
    status_filter: str = "All",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tuple[bool, List[Dict]]:
    """Return repayment rows for dashboard with optional filters and computed overdue status."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = (
            """
            SELECT
                lr.repayment_id,
                lr.loan_id,
                lr.member_id,
                m.staff_number,
                m.full_name,
                lr.installment_no,
                lr.due_date,
                lr.payment_date,
                lr.principal_due,
                lr.interest_due,
                lr.total_due,
                lr.principal_paid,
                lr.interest_paid,
                lr.total_paid,
                lr.status,
                CASE
                    WHEN LOWER(COALESCE(lr.status, '')) != 'paid'
                         AND lr.due_date IS NOT NULL
                         AND DATE(lr.due_date) < DATE('now')
                    THEN 'Overdue'
                    WHEN LOWER(COALESCE(lr.status, '')) = 'paid'
                    THEN 'Paid'
                    WHEN LOWER(COALESCE(lr.status, '')) = 'partial'
                    THEN 'Partial'
                    ELSE 'Pending'
                END AS dashboard_status
            FROM loan_repayments lr
            JOIN members m ON m.member_id = lr.member_id
            WHERE 1=1
            """
        )
        params: List[object] = []

        if member_id is not None:
            query += " AND lr.member_id = ?"
            params.append(int(member_id))
        if start_date:
            query += " AND DATE(COALESCE(lr.payment_date, lr.due_date)) >= DATE(?)"
            params.append(start_date)
        if end_date:
            query += " AND DATE(COALESCE(lr.payment_date, lr.due_date)) <= DATE(?)"
            params.append(end_date)

        query += " ORDER BY DATE(COALESCE(lr.due_date, lr.payment_date)) ASC, lr.installment_no ASC"

        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]

        normalized = (status_filter or "All").strip().lower()
        if normalized and normalized != "all":
            rows = [row for row in rows if str(row.get("dashboard_status", "")).lower() == normalized]

        return True, rows
    except Exception:
        return False, []
    finally:
        if conn:
            conn.close()


def get_repayment_dashboard_summary(
    db_path: str,
    member_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tuple[bool, Dict[str, float]]:
    """Return aggregated repayment KPIs for dashboard cards."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = (
            """
            SELECT
                COUNT(*) AS total_installments,
                COALESCE(SUM(COALESCE(total_due, 0.0)), 0.0) AS total_due,
                COALESCE(SUM(COALESCE(total_paid, 0.0)), 0.0) AS total_paid,
                COALESCE(SUM(
                    CASE
                        WHEN LOWER(COALESCE(status, '')) != 'paid'
                             AND due_date IS NOT NULL
                             AND DATE(due_date) < DATE('now')
                        THEN 1 ELSE 0
                    END
                ), 0) AS overdue_count,
                COALESCE(SUM(
                    CASE
                        WHEN LOWER(COALESCE(status, '')) = 'paid' THEN 1 ELSE 0
                    END
                ), 0) AS paid_count,
                COALESCE(SUM(
                    CASE
                        WHEN LOWER(COALESCE(status, '')) = 'partial' THEN 1 ELSE 0
                    END
                ), 0) AS partial_count,
                COALESCE(SUM(
                    CASE
                        WHEN LOWER(COALESCE(status, '')) NOT IN ('paid', 'partial')
                             AND (due_date IS NULL OR DATE(due_date) >= DATE('now'))
                        THEN 1 ELSE 0
                    END
                ), 0) AS pending_count,
                COALESCE(SUM(
                    CASE
                        WHEN LOWER(COALESCE(status, '')) != 'paid'
                             AND due_date IS NOT NULL
                             AND DATE(due_date) >= DATE('now')
                             AND DATE(due_date) <= DATE('now', '+7 day')
                        THEN 1 ELSE 0
                    END
                ), 0) AS due_this_week_count
            FROM loan_repayments
            WHERE 1=1
            """
        )
        params: List[object] = []

        if member_id is not None:
            query += " AND member_id = ?"
            params.append(int(member_id))
        if start_date:
            query += " AND DATE(COALESCE(payment_date, due_date)) >= DATE(?)"
            params.append(start_date)
        if end_date:
            query += " AND DATE(COALESCE(payment_date, due_date)) <= DATE(?)"
            params.append(end_date)

        cursor.execute(query, params)
        row = cursor.fetchone() or (0, 0.0, 0.0, 0, 0, 0, 0, 0)

        total_installments = float(row[0] or 0.0)
        total_due = float(row[1] or 0.0)
        total_paid = float(row[2] or 0.0)
        overdue_count = float(row[3] or 0.0)
        paid_count = float(row[4] or 0.0)
        partial_count = float(row[5] or 0.0)
        pending_count = float(row[6] or 0.0)
        due_this_week_count = float(row[7] or 0.0)
        total_outstanding = max(0.0, total_due - total_paid)
        collection_rate = (total_paid / total_due * 100.0) if total_due > 0 else 0.0

        return True, {
            "total_installments": total_installments,
            "total_due": round(total_due, 2),
            "total_paid": round(total_paid, 2),
            "total_outstanding": round(total_outstanding, 2),
            "overdue_count": overdue_count,
            "paid_count": paid_count,
            "partial_count": partial_count,
            "pending_count": pending_count,
            "due_this_week_count": due_this_week_count,
            "collection_rate": round(collection_rate, 2),
        }
    except Exception:
        return False, {
            "total_installments": 0.0,
            "total_due": 0.0,
            "total_paid": 0.0,
            "total_outstanding": 0.0,
            "overdue_count": 0.0,
            "paid_count": 0.0,
            "partial_count": 0.0,
            "pending_count": 0.0,
            "due_this_week_count": 0.0,
            "collection_rate": 0.0,
        }
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
            SELECT id, trans_date, trans_type, amount, running_balance, payment_mode, transfer_reference
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


def get_member_statement_data(
    db_path: str,
    member_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tuple[bool, Dict]:
    """Return member statement sections with optional date filters."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        params: List[object] = [member_id]
        savings_query = (
            """
            SELECT id, trans_date, trans_type, amount, running_balance, payment_mode, transfer_reference
            FROM savings_transactions
            WHERE member_id = ?
            """
        )
        if start_date:
            savings_query += " AND DATE(trans_date) >= DATE(?)"
            params.append(start_date)
        if end_date:
            savings_query += " AND DATE(trans_date) <= DATE(?)"
            params.append(end_date)
        savings_query += " ORDER BY id DESC"
        cursor.execute(savings_query, params)
        savings = [dict(row) for row in cursor.fetchall()]

        loan_params: List[object] = [member_id]
        loan_query = (
            """
            SELECT l.loan_id, l.principal, l.interest_rate, l.duration_months, l.status, l.date_issued,
                   l.principal_paid, l.interest_paid, l.total_repaid,
                   COALESCE(lp.name, 'Unspecified') AS loan_type
            FROM loans l
            LEFT JOIN loan_products lp ON lp.product_id = l.product_id
            WHERE l.member_id = ?
            """
        )
        if start_date:
            loan_query += " AND DATE(l.date_issued) >= DATE(?)"
            loan_params.append(start_date)
        if end_date:
            loan_query += " AND DATE(l.date_issued) <= DATE(?)"
            loan_params.append(end_date)
        loan_query += " ORDER BY l.loan_id DESC"
        cursor.execute(loan_query, loan_params)
        loans = [dict(row) for row in cursor.fetchall()]

        repay_params: List[object] = [member_id]
        repay_query = (
            """
            SELECT repayment_id, loan_id, installment_no, due_date,
                   principal_due, interest_due, total_due,
                   principal_paid, interest_paid, total_paid, status, payment_date
            FROM loan_repayments
            WHERE member_id = ?
            """
        )
        if start_date:
            repay_query += " AND DATE(COALESCE(payment_date, due_date)) >= DATE(?)"
            repay_params.append(start_date)
        if end_date:
            repay_query += " AND DATE(COALESCE(payment_date, due_date)) <= DATE(?)"
            repay_params.append(end_date)
        repay_query += " ORDER BY repayment_id DESC"
        cursor.execute(repay_query, repay_params)
        repayments = [dict(row) for row in cursor.fetchall()]

        return True, {
            "savings": savings,
            "loans": loans,
            "repayments": repayments,
        }
    except Exception:
        return False, {"savings": [], "loans": [], "repayments": []}
    finally:
        if conn:
            conn.close()


def get_society_report_stats(
    db_path: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_savings: bool = True,
    include_loans: bool = True,
    include_repayments: bool = True,
) -> Tuple[bool, Dict]:
    """Return period-based society totals for dynamic reports."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM members")
        total_members = int(cursor.fetchone()[0] or 0)

        total_savings = 0.0
        if include_savings:
            savings_query = (
                """
                SELECT COALESCE(SUM(
                    CASE
                        WHEN trans_type IN ('Lodgment', 'Opening Balance') THEN amount
                        WHEN trans_type = 'Deduction' THEN -amount
                        ELSE 0
                    END
                ), 0.0)
                FROM savings_transactions
                WHERE 1=1
                """
            )
            params: List[object] = []
            if start_date:
                savings_query += " AND DATE(trans_date) >= DATE(?)"
                params.append(start_date)
            if end_date:
                savings_query += " AND DATE(trans_date) <= DATE(?)"
                params.append(end_date)
            cursor.execute(savings_query, params)
            total_savings = float(cursor.fetchone()[0] or 0.0)

        total_loans_disbursed = 0.0
        avg_duration = 0.0
        if include_loans:
            loan_query = "SELECT COALESCE(SUM(principal), 0.0), COALESCE(AVG(duration_months), 0.0) FROM loans WHERE 1=1"
            loan_params: List[object] = []
            if start_date:
                loan_query += " AND DATE(date_issued) >= DATE(?)"
                loan_params.append(start_date)
            if end_date:
                loan_query += " AND DATE(date_issued) <= DATE(?)"
                loan_params.append(end_date)
            cursor.execute(loan_query, loan_params)
            loan_row = cursor.fetchone() or (0.0, 0.0)
            total_loans_disbursed = float(loan_row[0] or 0.0)
            avg_duration = float(loan_row[1] or 0.0)

        total_repayments = 0.0
        if include_repayments:
            repay_query = "SELECT COALESCE(SUM(total_paid), 0.0) FROM loan_repayments WHERE status IN ('Partial', 'Paid')"
            repay_params: List[object] = []
            if start_date:
                repay_query += " AND DATE(COALESCE(payment_date, due_date)) >= DATE(?)"
                repay_params.append(start_date)
            if end_date:
                repay_query += " AND DATE(COALESCE(payment_date, due_date)) <= DATE(?)"
                repay_params.append(end_date)
            cursor.execute(repay_query, repay_params)
            total_repayments = float(cursor.fetchone()[0] or 0.0)

        projected_interest = round(total_loans_disbursed * 0.12, 2)
        return True, {
            "total_members": total_members,
            "total_savings": round(total_savings, 2),
            "total_loans_disbursed": round(total_loans_disbursed, 2),
            "total_repayments": round(total_repayments, 2),
            "average_duration_months": round(avg_duration, 2),
            "total_projected_interest": projected_interest,
            "members_dividend_share": round(projected_interest * 0.60, 2),
            "society_dividend_share": round(projected_interest * 0.40, 2),
        }
    except Exception:
        return False, {}
    finally:
        if conn:
            conn.close()


def get_report_date_bounds(db_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Return earliest and latest reportable dates across savings, loans and repayments."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT MIN(report_date), MAX(report_date)
            FROM (
                SELECT DATE(trans_date) AS report_date
                FROM savings_transactions
                WHERE trans_date IS NOT NULL

                UNION ALL

                SELECT DATE(date_issued) AS report_date
                FROM loans
                WHERE date_issued IS NOT NULL

                UNION ALL

                SELECT DATE(due_date) AS report_date
                FROM loan_repayments
                WHERE due_date IS NOT NULL

                UNION ALL

                SELECT DATE(payment_date) AS report_date
                FROM loan_repayments
                WHERE payment_date IS NOT NULL
            )
            WHERE report_date IS NOT NULL
            """
        )
        row = cursor.fetchone()
        if not row:
            return True, None, None

        min_date = row[0]
        max_date = row[1]
        return True, min_date, max_date
    except Exception:
        return False, None, None
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
