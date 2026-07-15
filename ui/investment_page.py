"""
Investment page for SwiftLedger.
Lets the user record society investments (bonds, stocks, fixed deposits, etc.)
and review the investment portfolio.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QFormLayout,
    QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QMessageBox, QFrame, QScrollArea,
    QStackedWidget, QHeaderView, QInputDialog,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from ui.widgets import HorizontalNavBar, UppercaseLineEdit
from database.queries import (
    add_investment, get_investments, get_investment_summary, delete_investment,
)
from database.db_init import log_event
from utils import format_currency, get_icon

INVESTMENT_TYPES = [
    "Bond",
    "Bank Savings",
    "Treasury Bills",
    "Stocks",
    "Fixed Deposit",
    "Commercial Papers",
    "Mutual Funds",
]


class InvestmentPage(QWidget):
    """Record and review society investments."""

    def __init__(self, db_path: str = "swiftledger.db"):
        super().__init__()
        self.db_path = db_path
        self._build_ui()
        self.refresh_page()

    # ── UI ─────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(18)

        title = QLabel("Investments")
        title_font = QFont("Arial", 18)
        title_font.setBold(True)
        title.setFont(title_font)
        main.addWidget(title)

        # ── Horizontal nav bar ─────────────────────────────────────
        self.nav_bar = HorizontalNavBar(["Add Record", "Portfolio"])
        main.addWidget(self.nav_bar)

        self.stack = QStackedWidget()
        main.addWidget(self.stack)

        self._build_add_tab()
        self._build_portfolio_tab()

        self.nav_bar.currentChanged.connect(self.stack.setCurrentIndex)

        main.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _build_add_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(18)

        group = QGroupBox("New Investment Record")
        group.setFont(QFont("Arial", 12))
        form = QFormLayout(group)
        form.setContentsMargins(14, 20, 14, 14)
        form.setSpacing(12)

        self.input_instrument = UppercaseLineEdit()
        self.input_instrument.setMinimumHeight(34)
        self.input_instrument.setPlaceholderText("e.g. FGN Bond 2030")
        form.addRow("Financial Instrument:", self.input_instrument)

        self.input_holder = UppercaseLineEdit()
        self.input_holder.setMinimumHeight(34)
        self.input_holder.setPlaceholderText("e.g. SwiftLedger Society")
        form.addRow("Holder's Name:", self.input_holder)

        self.combo_type = QComboBox()
        self.combo_type.setMinimumHeight(34)
        self.combo_type.addItems(INVESTMENT_TYPES)
        self.combo_type.addItem("+ Add Type...")
        self.combo_type.setCurrentText(INVESTMENT_TYPES[0])
        self.combo_type.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Type:", self.combo_type)

        self.input_amount = QDoubleSpinBox()
        self.input_amount.setRange(0.0, 1_000_000_000.0)
        self.input_amount.setDecimals(2)
        self.input_amount.setPrefix("₦")
        self.input_amount.setSingleStep(1000.0)
        self.input_amount.setMinimumHeight(34)
        form.addRow("Invested Amount:", self.input_amount)

        self.input_interest = QDoubleSpinBox()
        self.input_interest.setRange(0.0, 100.0)
        self.input_interest.setDecimals(2)
        self.input_interest.setSuffix(" %")
        self.input_interest.setSingleStep(0.25)
        self.input_interest.setMinimumHeight(34)
        form.addRow("Expected Interest:", self.input_interest)

        self.date_duration = QDateEdit()
        self.date_duration.setCalendarPopup(True)
        self.date_duration.setDate(QDate.currentDate().addYears(1))
        self.date_duration.setMinimumHeight(34)
        form.addRow("Duration (maturity date):", self.date_duration)

        self.input_notes = UppercaseLineEdit(force_uppercase=False)
        self.input_notes.setMinimumHeight(34)
        self.input_notes.setPlaceholderText("Optional notes")
        form.addRow("Notes:", self.input_notes)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_save = QPushButton("Save Investment")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setMinimumWidth(160)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; border-radius: 6px; "
            "font-weight: bold; padding: 8px 20px; } "
            "QPushButton:hover { background-color: #2ecc71; }"
        )
        self.btn_save.clicked.connect(self._save_investment)
        btn_row.addWidget(self.btn_save)
        form.addRow(btn_row)

        layout.addWidget(group)
        layout.addStretch()
        self.stack.addWidget(tab)

    def _on_type_changed(self, text: str) -> None:
        if text == "+ Add Type...":
            new_type, ok = QInputDialog.getText(self, "Add Investment Type", "Enter new investment type:")
            new_type = new_type.strip()
            if ok and new_type:
                self.combo_type.insertItem(len(INVESTMENT_TYPES), new_type)
                INVESTMENT_TYPES.append(new_type)
                self.combo_type.setCurrentText(new_type)
            else:
                self.combo_type.setCurrentText(INVESTMENT_TYPES[0])

    def _save_investment(self) -> None:
        instrument = self.input_instrument.text().strip()
        holder = self.input_holder.text().strip()
        inv_type = self.combo_type.currentText().strip()
        if inv_type == "+ Add Type...":
            inv_type = INVESTMENT_TYPES[0]
        amount = self.input_amount.value()
        interest = self.input_interest.value()
        duration = self.date_duration.date().toString("yyyy-MM-dd")
        notes = self.input_notes.text().strip()

        if not instrument or not holder:
            QMessageBox.warning(self, "Missing Fields", "Instrument name and holder name are required.")
            return
        if amount <= 0:
            QMessageBox.warning(self, "Invalid Amount", "Invested amount must be greater than zero.")
            return

        success, message = add_investment(
            self.db_path, instrument, holder, inv_type, amount, interest, duration, notes
        )
        if not success:
            QMessageBox.critical(self, "Error", message)
            return

        log_event(
            user="Admin", category="Investment",
            description=f"Recorded investment: {instrument} ({inv_type}) ₦{amount:,.2f}",
            status="Success", db_path=self.db_path,
        )
        QMessageBox.information(self, "Saved", message)
        self._reset_form()
        self.refresh_page()

    def _reset_form(self) -> None:
        self.input_instrument.clear()
        self.input_holder.clear()
        self.combo_type.setCurrentText(INVESTMENT_TYPES[0])
        self.input_amount.setValue(0.0)
        self.input_interest.setValue(0.0)
        self.date_duration.setDate(QDate.currentDate().addYears(1))
        self.input_notes.clear()

    def _build_portfolio_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(18)

        self.summary_layout = QHBoxLayout()
        self.summary_layout.setSpacing(16)
        layout.addLayout(self.summary_layout)

        group = QGroupBox("Investment Portfolio")
        group.setFont(QFont("Arial", 12))
        group_layout = QVBoxLayout(group)

        self.table_investments = QTableWidget()
        self.table_investments.setColumnCount(7)
        self.table_investments.setHorizontalHeaderLabels(
            ["Instrument", "Holder", "Type", "Amount", "Exp. Interest", "Maturity", "Actions"]
        )
        self.table_investments.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_investments.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_investments.verticalHeader().setVisible(False)
        self.table_investments.setAlternatingRowColors(True)
        header = self.table_investments.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        group_layout.addWidget(self.table_investments)

        layout.addWidget(group)
        layout.addStretch()
        self.stack.addWidget(tab)

    # ── Data ───────────────────────────────────────────────────────

    def refresh_page(self) -> None:
        """Reload summary cards and portfolio table."""
        self._refresh_summary()
        self._refresh_table()

    def _refresh_summary(self) -> None:
        ok, summary = get_investment_summary(self.db_path)
        if not ok:
            return
        while self.summary_layout.count():
            item = self.summary_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        cards = [
            ("Investments", str(summary.get("investment_count", 0)), "#3498db", "fa5s.chart-pie"),
            ("Total Invested", format_currency(summary.get("total_invested", 0.0), symbol="₦"), "#27ae60", "fa5s.briefcase"),
            ("Expected Interest", format_currency(summary.get("total_expected_interest", 0.0), symbol="₦"), "#e67e22", "fa5s.chart-line"),
        ]
        for title, value, accent, icon_name in cards:
            self.summary_layout.addWidget(self._make_card(title, value, accent, icon_name))

    def _make_card(self, title: str, value: str, accent: str, icon_name: str = None) -> QFrame:
        card = QFrame()
        card.setMinimumHeight(90)
        card.setStyleSheet(
            f"QFrame {{ background-color: #2b2b2b; border-left: 4px solid {accent}; "
            f"border-radius: 8px; padding: 12px; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(6)
        if icon_name:
            icon_label = QLabel()
            icon_label.setPixmap(get_icon(icon_name, color=accent).pixmap(18, 18))
            icon_label.setStyleSheet("border: none;")
            title_row.addWidget(icon_label)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #bdc3c7; font-size: 12px; border: none;")
        title_row.addWidget(lbl_title)
        title_row.addStretch()
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(f"color: {accent}; font-size: 18px; font-weight: bold; border: none;")
        layout.addLayout(title_row)
        layout.addWidget(lbl_value)
        layout.addStretch()
        return card

    def _refresh_table(self) -> None:
        ok, rows = get_investments(self.db_path)
        if not ok:
            return
        self.table_investments.setRowCount(0)
        for row_idx, inv in enumerate(rows):
            self.table_investments.insertRow(row_idx)
            self.table_investments.setItem(row_idx, 0, QTableWidgetItem(str(inv.get("instrument_name") or "")))
            self.table_investments.setItem(row_idx, 1, QTableWidgetItem(str(inv.get("holder_name") or "")))
            self.table_investments.setItem(row_idx, 2, QTableWidgetItem(str(inv.get("inv_type") or "")))
            self.table_investments.setItem(row_idx, 3, QTableWidgetItem(format_currency(float(inv.get("invested_amount") or 0.0), symbol="₦")))
            self.table_investments.setItem(row_idx, 4, QTableWidgetItem(f"{float(inv.get('expected_interest') or 0.0):.2f} %"))
            self.table_investments.setItem(row_idx, 5, QTableWidgetItem(str(inv.get("duration_date") or "—")))

            del_btn = QPushButton("Delete")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet(
                "QPushButton { background-color: #c0392b; color: white; border-radius: 4px; "
                "padding: 4px 10px; } QPushButton:hover { background-color: #e74c3c; }"
            )
            del_btn.clicked.connect(
                lambda _=False, iid=int(inv.get("investment_id")): self._delete_investment(iid)
            )
            self.table_investments.setCellWidget(row_idx, 6, del_btn)

    def _delete_investment(self, investment_id: int) -> None:
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            "Delete this investment record? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        success, message = delete_investment(self.db_path, investment_id)
        if not success:
            QMessageBox.critical(self, "Error", message)
            return
        log_event(
            user="Admin", category="Investment",
            description=f"Deleted investment id={investment_id}",
            status="Success", db_path=self.db_path,
        )
        self.refresh_page()
