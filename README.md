# SwiftLedger 🚀

SwiftLedger is a professional-grade, multi-user thrift and credit-union management system designed to help small societies and cooperatives manage members, savings, loans, and repayments with a modern dark user interface.

## Key Features ✨
- **Member registration & management** — register members with unique staff numbers and track join dates.
- **Savings tracking** — record deductions and lodgments per member with a full transaction history.
- **Loan engine** — loans governed by a 2× savings rule (loan eligibility tied to member savings), with repayment scheduling and status tracking.
- **Modern Dark UI** — PySide6-based desktop UI with a high-contrast QSS stylesheet for accessibility and clarity.

## Tech Stack 🛠️
| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| GUI | PySide6 (Qt for Python) |
| Database | SQLite |

## Project Structure 📁
| Path | Purpose |
|---|---|
| `main.py` | Application launcher — bootstraps the Qt app and opens `MainWindow`. |
| `requirements.txt` | Project Python dependencies (e.g., PySide6). |
| `database/` | Database schema initialization and data access layer (DAL). |
| `ui/` | PySide6 UI code: `MainWindow`, pages, and widgets. |
| `logic/` | Business logic, loan & dividend engines, calculation helpers. |
| `assets/` | Static assets: icons, logos, QSS stylesheets. |

## Getting Started ▶️
1. Create a Python virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Initialize the database (the `db_init.py` script will create required tables):

```powershell
python -m database.db_init
```

3. Run the application:

```powershell
python main.py
```

## Next steps
- Implement detailed loan rules in `logic/loan_engine.py`.
- Add unit tests and CI workflow.
- Add user authentication and role-based access control if multi-user remote operation is required.

---
For more information about the database and UI internals, see `database/README.md` and `ui/README.md`.
