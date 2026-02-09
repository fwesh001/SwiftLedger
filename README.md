```markdown
# SwiftLedger

SwiftLedger is a local desktop application for managing small thrift societies and cooperatives. It provides member management, savings transaction tracking, loan origination and repayment scheduling, PDF reporting, and an audit trail — all in a compact PySide6 (Qt) GUI.

Quick highlights
- Member registration and lookup by staff number
- Savings transactions (lodgment/deduction) with running balances
- Loan issuance with business-rule checks and repayment schedules
- Branded PDF export for member statements and society summaries
- Audit logging for important events
- UI customization: light/dark theme and text scaling

Supported environment
- Python 3.10+ (3.11 recommended)
- Windows / macOS / Linux (Windows-only features: system authentication)
- SQLite local database (swiftledger.db)

Getting started
1. Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Initialize the database (creates schema and default settings):

```powershell
python -m database.db_init
```

3. Run the application:

```powershell
python main.py
```

How to use
- On first run the app opens a setup wizard to configure society name and initial credential.
- Use the left sidebar to navigate: Dashboard, Members, Savings, Loans, Reports, Audit Logs, Settings, About.
- Generate PDF reports in the Reports page. Use the Preview button to view them inside the app (requires Qt PDF modules) or Save to persist to disk.

Developer notes
- UI code is under `ui/` (main window and page widgets).
- Database schema and DAL are in `database/` (`db_init.py`, `queries.py`).
- Business rules (loan/dividend calculations) live under `logic/`.

Troubleshooting
- If PDF preview fails, install the Qt PDF components: upgrade PySide6 to a release with QtPdf and QtPdfWidgets.
- If saving a PDF fails with PermissionError, ensure the target file is not open in another program.

See `database/README.md`, `ui/README.md`, and `assets/README.md` for module-specific details.

```markdown
