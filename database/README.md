```markdown
# database — Schema & Data Access

This folder contains the SQLite schema initialization and the Data Access Layer (DAL) used by SwiftLedger.

Key tables
- `members` — member_id (PK), staff_number (UNIQUE), full_name, date_joined, current_savings, total_loans, created_at
- `savings_transactions` — individual lodgment/deduction records, linked to `members.member_id`
- `loans` — loan records with principal, interest_rate, status, date_issued, member_id
- `repayment_schedule` — per-loan installment plan rows (installment_no, expected_principal, expected_interest, due_date, status)
- `system_settings` — single-row configuration for UI and security settings (society_name, security_mode, auth_hash, theme, text_scale, etc.)

Where logic lives
- Schema creation and initial values: `database/db_init.py`
- Data access helper functions: `database/queries.py` (use these from UI/logic layers; do not access SQLite directly elsewhere)

Important notes
- Business rules such as the "2× savings" loan-eligibility rule are enforced in `logic/loan_engine.py` (application logic), not as DB constraints.
- `queries.py` uses parameterized SQL to avoid injection risks; prefer those helper functions for consistency.
- When altering the schema, add a migration step in `db_init.py` or introduce a simple migrations table to track and apply upgrades.

Developer tips
- Inspect the live database quickly:

```powershell
python -c "import sqlite3; conn=sqlite3.connect('swiftledger.db'); print(conn.execute('PRAGMA table_info(members)').fetchall()); conn.close()"
```

- Back up the database before making schema changes:

```powershell
copy swiftledger.db swiftledger.db.bak
```

If you need to add auditing or more advanced migration support, consider using a lightweight migration tool or keeping incremental SQL upgrade scripts under `database/migrations/`.

```
