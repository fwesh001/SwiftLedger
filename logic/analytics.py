"""
Analytics engine for SwiftLedger.

Provides financial metrics, trend analysis, and risk assessment functions.
"""

import sqlite3
from datetime import date, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict


def get_monthly_snapshot(db_path: str, year: int, month: int) -> Tuple[bool, Dict]:
    """
    Retrieve aggregated financial metrics for a specific month.

    Args:
        db_path: Path to the SQLite database.
        year: Year (e.g., 2024)
        month: Month (1-12)

    Returns:
        A tuple (success: bool, snapshot: Dict) containing:
        - total_savings_growth: Net change in total savings for the month
        - new_loans_disbursed: Sum of principal for loans issued that month
        - total_interest_earned: calculated from (new_loans_disbursed × avg_interest_rate)
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Beginning and end of month
        start_date = f"{year}-{month:02d}-01"
        end_day = 31 if month != 2 else 28  # Simplified; doesn't handle leap years perfectly
        if month == 2:
            next_month = 3
            next_year = year
        else:
            next_month = (month % 12) + 1
            next_year = year if month < 12 else year + 1
        end_date = f"{next_year}-{next_month:02d}-01"

        # Total savings transactions for the month
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0.0)
            FROM savings_transactions
            WHERE trans_date >= ? AND trans_date < ? AND trans_type = 'Lodgment'
        """, (start_date, end_date))
        lodgments = float(cursor.fetchone()[0] or 0.0)

        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0.0)
            FROM savings_transactions
            WHERE trans_date >= ? AND trans_date < ? AND trans_type = 'Deduction'
        """, (start_date, end_date))
        deductions = float(cursor.fetchone()[0] or 0.0)

        savings_growth = lodgments - deductions

        # New loans disbursed in the month
        cursor.execute("""
            SELECT COALESCE(SUM(principal), 0.0), COALESCE(AVG(interest_rate), 12.0)
            FROM loans
            WHERE date_issued >= ? AND date_issued < ?
        """, (start_date, end_date))
        row = cursor.fetchone()
        new_loans = float(row[0] or 0.0) if row else 0.0
        avg_rate = float(row[1] or 12.0) if row else 12.0

        # Interest earned (simplified: principal × rate / 12 months)
        interest_earned = (new_loans * avg_rate) / 100.0

        snapshot = {
            'year': year,
            'month': month,
            'total_savings_growth': round(savings_growth, 2),
            'new_loans_disbursed': round(new_loans, 2),
            'total_interest_earned': round(interest_earned, 2),
            'lodgments': round(lodgments, 2),
            'deductions': round(deductions, 2),
            'avg_interest_rate': round(avg_rate, 2),
        }
        return True, snapshot

    except sqlite3.DatabaseError:
        return False, {}
    except Exception:
        return False, {}
    finally:
        if conn:
            conn.close()


def get_monthly_trend(db_path: str, months: int = 12) -> Tuple[bool, Dict]:
    """
    Retrieve monthly aggregated savings and loans for the last $months months.

    Args:
        db_path: Path to the SQLite database.
        months: Number of months to retrieve (default: 12)

    Returns:
        A tuple (success: bool, trend: Dict) where trend contains:
        - months: List of "YYYY-MM" strings
        - savings: List of total member savings at month-end (aggregated)
        - loans: List of total outstanding loans at month-end (aggregated)
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Retrieve historical snapshots
        # We'll aggregate from members table as a point-in-time
        # For proper monthly history, we'd need a separate history table
        # For now, use savings_transactions and loans tables to infer

        month_list = []
        savings_list = []
        loans_list = []

        today = date.today()
        for i in range(months - 1, -1, -1):
            target_date = today - timedelta(days=30 * i)
            year_m = target_date.year
            month_m = target_date.month
            month_str = f"{year_m}-{month_m:02d}"

            # Savings at this point in time (cumulative from start to end of month)
            cursor.execute("""
                SELECT COALESCE(SUM(running_balance), 0.0)
                FROM (
                    SELECT member_id, MAX(running_balance) as running_balance
                    FROM savings_transactions
                    WHERE trans_date < DATE(?, '+1 month')
                    GROUP BY member_id
                )
            """, (f"{year_m}-{month_m:02d}-01",))
            total_savings = float(cursor.fetchone()[0] or 0.0)

            # Outstanding loans at this point in time
            cursor.execute("""
                SELECT COALESCE(SUM(principal), 0.0)
                FROM loans
                WHERE date_issued <= DATE(?, '+1 month') AND status != 'Paid'
            """, (f"{year_m}-{month_m:02d}-01",))
            total_loans = float(cursor.fetchone()[0] or 0.0)

            month_list.append(month_str)
            savings_list.append(round(total_savings, 2))
            loans_list.append(round(total_loans, 2))

        trend = {
            'months': month_list,
            'savings': savings_list,
            'loans': loans_list,
        }
        return True, trend

    except sqlite3.DatabaseError:
        return False, {}
    except Exception:
        return False, {}
    finally:
        if conn:
            conn.close()


def calculate_lts_ratio(db_path: str) -> Tuple[bool, float]:
    """
    Calculate the Loan-to-Savings (LTS) Ratio.

    Formula: LTS = (Total Outstanding Loans / Total Member Savings) × 100

    Returns:
        A tuple (success: bool, lts_ratio: float) where lts_ratio is a percentage.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COALESCE(SUM(total_loans), 0.0) FROM members;")
        total_loans = float(cursor.fetchone()[0] or 0.0)

        cursor.execute("SELECT COALESCE(SUM(current_savings), 0.0) FROM members;")
        total_savings = float(cursor.fetchone()[0] or 0.0)

        if total_savings == 0.0:
            return True, 0.0

        lts = (total_loans / total_savings) * 100.0
        return True, round(lts, 2)

    except sqlite3.DatabaseError:
        return False, 0.0
    except Exception:
        return False, 0.0
    finally:
        if conn:
            conn.close()


def get_liquidity_status(db_path: str) -> Tuple[bool, Dict]:
    """
    Determine liquidity and available cash position.

    Returns:
        A tuple (success: bool, status: Dict) containing:
        - available_cash: estimated as total_savings
        - outstanding_loans: total_loans_disbursed
        - liquidity_ratio: (available_cash / outstanding_loans)
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COALESCE(SUM(current_savings), 0.0) FROM members;")
        available = float(cursor.fetchone()[0] or 0.0)

        cursor.execute("SELECT COALESCE(SUM(total_loans), 0.0) FROM members;")
        outstanding = float(cursor.fetchone()[0] or 0.0)

        ratio = (available / outstanding) if outstanding > 0 else float('inf')

        status = {
            'available_cash': round(available, 2),
            'outstanding_loans': round(outstanding, 2),
            'liquidity_ratio': round(ratio, 2) if ratio != float('inf') else 999.99,
        }
        return True, status

    except sqlite3.DatabaseError:
        return False, {}
    except Exception:
        return False, {}
    finally:
        if conn:
            conn.close()
