```markdown
# ui — User Interface Overview

This folder contains the PySide6 (Qt for Python) UI implementation for SwiftLedger.

Architecture
- `ui/main_window.py` — `MainWindow` composes the left-hand sidebar and a `QStackedWidget` for pages.
- Each page is a focused `QWidget` in `ui/` (e.g., `reports_page.py`, `settings_page.py`, `members_page`), making them easy to test and extend.

Pages (summary)
- Dashboard — Overview metrics and quick actions (charts and stat cards).
- Members — Register members, edit, and delete. Uses `database.queries` helpers.
- Savings — Post lodgment/deduction transactions and view member savings history.
- Loans — Loan origination, approvals, repayment schedule generation.
- Reports — Generate and preview branded PDFs (member statements and society summaries).
- Audit Logs — View the recorded system events from `audit_logs`.
- Settings — Theme, text scale, security mode (PIN/Password/System Auth), and other preferences.

How to add a page
1. Create a new file under `ui/` with a `QWidget` subclass.
2. Implement the page UI and connect to `database.queries` or `logic/` as needed.
3. Register the page in `MainWindow.create_pages()` and add a sidebar button.

PDF preview
- The Reports page supports in-app PDF preview using Qt's `QPdfDocument` + `QPdfView`. This requires PySide6 builds that include `QtPdf` and `QtPdfWidgets`.
- If preview is unavailable, the app falls back to saving the PDF and opening it in an external viewer.

Styling
- The global stylesheet is in `assets/styles.qss`. Adjust variables there for consistent theming.

Developer tips
- Keep page logic thin: call into `database/queries.py` and `logic/*` for business rules.
- Reuse widgets from `ui/widgets.py` where helpful (common form rows, confirmation dialogs).

```
