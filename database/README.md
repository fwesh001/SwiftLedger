# database — Schema & Data Access 📦

This folder contains the SQLite schema initialization scripts and the Data Access Layer (DAL) used by SwiftLedger.

## Schema Overview 🗂️
The primary tables and their purpose:

- **Members**
  - Columns: `member_id` (PK), `staff_number` (UNIQUE), `full_name`, `date_joined`, `created_at`
  - Stores core member identity and join metadata.

- **Savings**
  - Columns: `savings_id` (PK), `member_id` (FK → Members.member_id), `amount`, `date`, `type` (`Deduction`/`Lodgment`), `created_at`
  - Stores each deduction or lodgment event per member.

- **Loans**
  - Columns: `loan_id` (PK), `member_id` (FK → Members.member_id), `principal`, `interest_rate`, `status`, `date_issued`, `created_at`
  - Represents loans issued to members, with status tracking (Active/Closed/Default).

- **RepaymentSchedule**
  - Columns: `schedule_id` (PK), `loan_id` (FK → Loans.loan_id), `installment_no`, `expected_principal`, `expected_interest`, `due_date`, `status`, `created_at`
  - A payment schedule tied to a loan, with per-installment expected principal/interest and status.

- **SystemSettings**
  - A single-row table for global variables (e.g., `min_monthly_saving`, `max_loan_amount`, `default_interest_rate`).

## Relationship Logic 🔗
- `Savings.member_id` and `Loans.member_id` reference `Members.member_id` (ON DELETE CASCADE). Deleting a member cascades to associated savings and loans.
- `RepaymentSchedule.loan_id` references `Loans.loan_id` (ON DELETE CASCADE) so schedules are removed if a loan is deleted.

### 2× Savings Loan Constraint
SwiftLedger enforces a business rule commonly used in thrift societies: a member's maximum eligible loan amount is limited to twice their total savings balance (2× savings). This is enforced at the business logic level (e.g., `logic/loan_engine.py`) during loan origination checks — not as a database constraint — because it requires aggregation and domain policy logic.

## Initialization & DAL 🧭
- `db_init.py` — Responsible for creating the SQLite file and all tables (uses `CREATE TABLE IF NOT EXISTS`) and inserting default settings into `SystemSettings`.
- `queries.py` — Acts as the Data Access Layer (DAL). It exposes functions such as `add_member`, `get_all_members`, `add_saving`, `get_member_savings`, and loan-related helpers. Keep database access centralized here.

## Notes & Best Practices ✅
- Use parameterized SQL to avoid injection risks (implemented in `queries.py`).
- Perform aggregate checks (like total savings) in the logic layer before writing loan records.
- Keep migrations or schema evolution in mind — for production use, consider adding a simple migrations mechanism (e.g., a version table with incremental upgrade scripts).
