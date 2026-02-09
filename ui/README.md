# ui — User Interface Overview 🖥️

This folder contains the PySide6 (Qt for Python) UI implementation for SwiftLedger.

## Architecture
- The main entry-point for the UI is `MainWindow` (`ui/main_window.py`). `MainWindow` composes a left-hand sidebar and a main content area implemented with `QStackedWidget` for page navigation.
- Each page is encapsulated in its own QWidget-derived class for separation of concerns and easier testing.

## Pages (Quick Guide) 📚
- **Dashboard** — Overview metrics and quick actions. (Placeholder for charts/stats)
- **Members** — Member registration form and an interactive members table. Uses `database.queries.add_member` and `get_all_members` for data access.
- **Savings** — Member search, transaction posting (lodgment/deduction), and per-member savings history. Integrates `add_saving`, `get_member_savings`, and `get_member_by_staff_number`.
- **Loans** — Loan origination, approval (2× savings check), and repayment schedule management (wire up to `logic/loan_engine.py`).

## Navigation
- Sidebar buttons switch the visible page in the `QStackedWidget` by changing the stacked widget index. The sidebar is implemented as a `QFrame` with flat-style `QPushButton` items.

## Styling
- The project uses a custom QSS stylesheet located in `assets/styles.qss`. The stylesheet implements a high-contrast dark theme (dark backgrounds, bright white/grey text) and provides consistent visuals for inputs, buttons, and tables.

## Extensibility
- Pages are intentionally small and focused; add new widgets or dialogs as separate modules under `ui/` and register them in `MainWindow.create_pages()`.
