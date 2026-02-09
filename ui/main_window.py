"""
Main application window for SwiftLedger.
Contains the sidebar navigation and stacked widget for multiple pages.
"""

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame,
    QPushButton, QStackedWidget, QLabel, QGroupBox, QFormLayout,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem, QMessageBox,
    QAbstractItemView, QDoubleSpinBox, QSpinBox, QDialog, QListWidget
)
from PySide6.QtCore import Qt, QSize, QEvent, QTimer
from PySide6.QtGui import QFont
from datetime import date
import sys
from pathlib import Path
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.queries import (
    add_member, get_all_members, get_member_by_staff_number,
    add_saving, get_total_savings, get_member_savings, get_system_settings,
    apply_for_loan, get_member_loans, calculate_repayment_schedule,
    get_society_stats, check_overdue_loans
)
from ui.audit_page import AuditLogPage
from ui.about_page import AboutPage
from ui.settings_page import SettingsPage
from ui.login_screen import LoginScreen


class DashboardPage(QWidget):
    """Dashboard page with society-wide financial statistics and dividend breakdown."""

    # Accent colours for each stat card (left-border & value text)
    CARD_COLOURS = {
        'members':  '#3498db',  # Blue
        'savings':  '#27ae60',  # Green
        'loans':    '#e67e22',  # Orange
        'interest': '#9b59b6',  # Purple
    }

    def __init__(self, db_path: str = "swiftledger.db"):
        super().__init__()
        self.db_path = db_path
        self._build_ui()

    # ── UI construction ─────────────────────────────────────────────

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Title row
        header_row = QHBoxLayout()
        title = QLabel("Dashboard")
        title_font = QFont("Arial", 20)
        title_font.setBold(True)
        title.setFont(title_font)
        header_row.addWidget(title)
        header_row.addStretch()

        self.btn_refresh = QPushButton("⟳  Refresh")
        self.btn_refresh.setMinimumHeight(36)
        self.btn_refresh.setMinimumWidth(110)
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet(
            "QPushButton { background-color: #2980b9; color: white; border-radius: 6px; "
            "font-weight: bold; padding: 6px 14px; } "
            "QPushButton:hover { background-color: #3498db; }"
        )
        self.btn_refresh.clicked.connect(self.refresh_dashboard)
        header_row.addWidget(self.btn_refresh)
        main_layout.addLayout(header_row)

        # ── Stat cards row ──────────────────────────────────────────
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.card_members = self._create_stat_card(
            "👥  Total Members", "0", self.CARD_COLOURS['members']
        )
        self.card_savings = self._create_stat_card(
            "💰  Total Savings", "₦0.00", self.CARD_COLOURS['savings']
        )
        self.card_loans = self._create_stat_card(
            "🏦  Loans Disbursed", "₦0.00", self.CARD_COLOURS['loans']
        )
        self.card_interest = self._create_stat_card(
            "📈  Projected Interest", "₦0.00", self.CARD_COLOURS['interest']
        )

        for card, _, _ in [
            self.card_members, self.card_savings,
            self.card_loans, self.card_interest
        ]:
            cards_layout.addWidget(card)

        main_layout.addLayout(cards_layout)

        # ── Dividend section ────────────────────────────────────────
        dividend_group = QGroupBox("Dividend Breakdown")
        dividend_group.setFont(QFont("Arial", 12))
        dividend_group.setStyleSheet(
            "QGroupBox { border: 1px solid #34495e; border-radius: 8px; "
            "margin-top: 14px; padding: 18px 14px 14px 14px; color: #ecf0f1; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 14px; "
            "padding: 0 6px; color: #bdc3c7; }"
        )
        div_layout = QHBoxLayout(dividend_group)
        div_layout.setSpacing(20)

        self.member_div_card = self._create_dividend_card(
            "Members' Share (60%)", "₦0.00", "#27ae60"
        )
        self.society_div_card = self._create_dividend_card(
            "Society Reserve (40%)", "₦0.00", "#e74c3c"
        )

        div_layout.addWidget(self.member_div_card[0])
        div_layout.addWidget(self.society_div_card[0])

        main_layout.addWidget(dividend_group)

        # ── Alerts + Visuals row ────────────────────────────────────
        alerts_row = QHBoxLayout()
        alerts_row.setSpacing(16)

        alerts_group = QGroupBox("Loan Alerts")
        alerts_group.setFont(QFont("Arial", 12))
        alerts_layout = QVBoxLayout(alerts_group)
        self.list_overdue = QListWidget()
        self.list_overdue.setMinimumHeight(120)
        alerts_layout.addWidget(self.list_overdue)
        alerts_row.addWidget(alerts_group)

        health_group = QGroupBox("Financial Health")
        health_group.setFont(QFont("Arial", 12))
        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_placeholder = QLabel("Charts disabled")
        self.chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_layout.addWidget(self.chart_placeholder)
        health_layout = QVBoxLayout(health_group)
        health_layout.addWidget(self.chart_container)
        alerts_row.addWidget(health_group)

        main_layout.addLayout(alerts_row)

        # ── Status bar ──────────────────────────────────────────────
        self.lbl_status = QLabel("Last refreshed: —")
        self.lbl_status.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self.lbl_status)

        main_layout.addStretch()

    # ── Widget factories ────────────────────────────────────────────

    def _create_stat_card(
        self, title_text: str, value_text: str, accent: str
    ) -> tuple:
        """Return (QFrame card, QLabel title, QLabel value)."""
        card = QFrame()
        card.setMinimumHeight(120)
        card.setStyleSheet(
            f"QFrame {{ background-color: #2b2b2b; border-left: 4px solid {accent}; "
            f"border-radius: 8px; padding: 14px; }}"
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        lbl_title = QLabel(title_text)
        lbl_title.setStyleSheet("color: #bdc3c7; font-size: 12px; border: none;")

        lbl_value = QLabel(value_text)
        lbl_value.setStyleSheet(
            f"color: {accent}; font-size: 22px; font-weight: bold; border: none;"
        )

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        layout.addStretch()

        return card, lbl_title, lbl_value

    def _create_dividend_card(
        self, title_text: str, value_text: str, accent: str
    ) -> tuple:
        """Return (QFrame card, QLabel value)."""
        card = QFrame()
        card.setMinimumHeight(100)
        card.setStyleSheet(
            f"QFrame {{ background-color: #2b2b2b; border: 1px solid {accent}; "
            f"border-radius: 10px; padding: 16px; }}"
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        lbl_title = QLabel(title_text)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet("color: #bdc3c7; font-size: 13px; border: none;")

        lbl_value = QLabel(value_text)
        lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_value.setStyleSheet(
            f"color: {accent}; font-size: 26px; font-weight: bold; border: none;"
        )

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)

        return card, lbl_value

    # ── Refresh logic ───────────────────────────────────────────────

    def refresh_dashboard(self) -> None:
        """Fetch society stats from the database and update every label."""
        success, stats = get_society_stats(self.db_path)
        if not success:
            self.lbl_status.setText("⚠  Failed to load statistics")
            return

        settings_ok, settings = get_system_settings(self.db_path)
        show_charts = bool(settings.get('show_charts', 0)) if settings_ok and settings else False

        # Stat cards
        self.card_members[2].setText(str(stats.get('total_members', 0)))
        self.card_savings[2].setText(f"₦{stats.get('total_savings', 0):,.2f}")
        self.card_loans[2].setText(f"₦{stats.get('total_loans_disbursed', 0):,.2f}")
        self.card_interest[2].setText(f"₦{stats.get('total_projected_interest', 0):,.2f}")

        # Dividend cards
        self.member_div_card[1].setText(
            f"₦{stats.get('members_dividend_share', 0):,.2f}"
        )
        self.society_div_card[1].setText(
            f"₦{stats.get('society_dividend_share', 0):,.2f}"
        )

        self._update_overdue_alerts()
        self._update_financial_health_chart(stats, show_charts)

        # Timestamp
        from datetime import datetime
        self.lbl_status.setText(
            f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def _update_overdue_alerts(self) -> None:
        ok, overdue = check_overdue_loans(self.db_path)
        self.list_overdue.clear()
        if not ok:
            self.list_overdue.addItem("Failed to load alerts")
            return
        if not overdue:
            self.list_overdue.addItem("No late payments")
            return
        for item in overdue:
            label = (
                f"⚠ Loan #{item['loan_id']} - {item['full_name']} "
                f"({item['staff_number']}) due {item['due_date']}"
            )
            self.list_overdue.addItem(label)

    def _update_financial_health_chart(self, stats: dict, show_charts: bool) -> None:
        if not show_charts:
            self._set_chart_placeholder("Charts disabled")
            return

        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        except Exception:
            self._set_chart_placeholder("Install matplotlib to view charts")
            return

        total_savings = float(stats.get('total_savings', 0.0))
        total_loans = float(stats.get('total_loans_disbursed', 0.0))
        available_cash = max(total_savings - total_loans, 0.0)

        self._clear_chart_layout()
        fig = Figure(figsize=(4, 3))
        ax = fig.add_subplot(111)
        ax.pie(
            [available_cash, total_loans],
            labels=["Available Cash", "Outstanding Loans"],
            autopct='%1.1f%%',
            startangle=90
        )
        ax.axis('equal')
        canvas = FigureCanvas(fig)
        self.chart_layout.addWidget(canvas)

    def _set_chart_placeholder(self, text: str) -> None:
        self._clear_chart_layout()
        self.chart_placeholder = QLabel(text)
        self.chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_layout.addWidget(self.chart_placeholder)

    def _clear_chart_layout(self) -> None:
        while self.chart_layout.count():
            item = self.chart_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)


class MembersPage(QWidget):
    """Page for Members management with registration form and member table."""
    
    def __init__(self, db_path: str = "swiftledger.db"):
        super().__init__()
        self.db_path = db_path
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Title
        title = QLabel("Members Management")
        title_font = QFont("Arial", 18)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)
        
        # Registration Form Group
        form_group = QGroupBox("Register New Member")
        form_font = QFont("Arial", 10)
        form_font.setBold(True)
        form_group.setFont(form_font)
        form_layout = QFormLayout()
        
        # Staff Number input
        self.input_staff_number = QLineEdit()
        self.input_staff_number.setPlaceholderText("e.g., EMP001")
        form_layout.addRow("Staff Number:", self.input_staff_number)
        
        # Full Name input
        self.input_full_name = QLineEdit()
        self.input_full_name.setPlaceholderText("e.g., John Doe")
        form_layout.addRow("Full Name:", self.input_full_name)

        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)
        
        # Register button
        button_layout = QHBoxLayout()
        self.btn_register = QPushButton("Register Member")
        self.btn_register.setMinimumHeight(40)
        btn_font = QFont("Arial", 10)
        btn_font.setBold(True)
        self.btn_register.setFont(btn_font)
        self.btn_register.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #229954;
            }
        """)
        self.btn_register.clicked.connect(self.register_member)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_register, 0, Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(button_layout)
        
        # Members Table
        table_title = QLabel("All Members")
        table_font = QFont("Arial", 12)
        table_font.setBold(True)
        table_title.setFont(table_font)
        main_layout.addWidget(table_title)
        
        self.table_members = QTableWidget()
        self.table_members.setColumnCount(5)
        self.table_members.setHorizontalHeaderLabels([
            "Staff Number", "Full Name", "Phone", "Current Savings", "Total Loans"
        ])
        self.table_members.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_members.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_members.horizontalHeader().setStretchLastSection(True)
        main_layout.addWidget(self.table_members)
        
        self.setLayout(main_layout)
        
        # Load initial data
        self.load_data()
    
    def register_member(self) -> None:
        """Handle member registration."""
        
        # Validate inputs
        staff_number = self.input_staff_number.text().strip()
        full_name = self.input_full_name.text().strip()
        
        if not staff_number or not full_name:
            QMessageBox.warning(self, "Invalid Input", "Please fill in all required fields.")
            return
        
        # Prepare member data
        member_data = {
            'staff_number': staff_number,
            'full_name': full_name,
        }
        
        # Add member to database
        success, message = add_member(self.db_path, member_data)
        
        if success:
            QMessageBox.information(self, "Success", message)
            # Clear inputs
            self.input_staff_number.clear()
            self.input_full_name.clear()
            # Refresh table
            self.load_data()
        else:
            QMessageBox.critical(self, "Error", message)
    
    def load_data(self) -> None:
        """Load and display all members in the table."""
        
        try:
            success, members = get_all_members(self.db_path)
            
            if not success or not members:
                self.table_members.setRowCount(0)
                return
            
            # Clear existing rows
            self.table_members.setRowCount(0)
            
            # Populate table
            for row_idx, member in enumerate(members):
                self.table_members.insertRow(row_idx)
                
                # Staff Number
                staff_num_item = QTableWidgetItem(member.get('staff_number', 'N/A'))
                self.table_members.setItem(row_idx, 0, staff_num_item)
                
                # Full Name
                name_item = QTableWidgetItem(member.get('full_name', 'N/A'))
                self.table_members.setItem(row_idx, 1, name_item)
                
                # Phone
                phone_item = QTableWidgetItem(member.get('phone', 'N/A'))
                self.table_members.setItem(row_idx, 2, phone_item)

                # Current Savings
                savings = float(member.get('current_savings', 0.0) or 0.0)
                savings_item = QTableWidgetItem(f"₦{savings:,.2f}")
                savings_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                self.table_members.setItem(row_idx, 3, savings_item)

                # Total Loans
                loans = float(member.get('total_loans', 0.0) or 0.0)
                loans_item = QTableWidgetItem(f"₦{loans:,.2f}")
                loans_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                self.table_members.setItem(row_idx, 4, loans_item)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load members: {str(e)}")


class SavingsPage(QWidget):
    """Page for Savings management with search, transaction form, and history."""
    
    def __init__(self, db_path: str = "swiftledger.db"):
        super().__init__()
        self.db_path = db_path
        self.current_member_id = None
        self.current_member_name = None
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Title
        title = QLabel("Savings Management")
        title_font = QFont("Arial", 18)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)
        
        # Search Section
        search_group = QGroupBox("Find Member")
        search_font = QFont("Arial", 10)
        search_font.setBold(True)
        search_group.setFont(search_font)
        search_layout = QHBoxLayout()
        
        search_label = QLabel("Staff Number:")
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("e.g., EMP001")
        self.btn_search = QPushButton("Search")
        self.btn_search.setMinimumWidth(100)
        self.btn_search.clicked.connect(self.search_member)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.input_search)
        search_layout.addWidget(self.btn_search)
        search_layout.addStretch()
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)
        
        # Member Info Section
        info_group = QGroupBox("Member Information")
        info_font = QFont("Arial", 10)
        info_font.setBold(True)
        info_group.setFont(info_font)
        info_layout = QHBoxLayout()
        
        self.label_member_name = QLabel("Name: Not Selected")
        self.label_member_name.setFont(QFont("Arial", 11))
        
        self.label_total_savings = QLabel("Total Savings: ₦0.00")
        self.label_total_savings.setFont(QFont("Arial", 11))
        savings_font = QFont("Arial", 11)
        savings_font.setBold(True)
        self.label_total_savings.setFont(savings_font)
        
        info_layout.addWidget(self.label_member_name)
        info_layout.addStretch()
        info_layout.addWidget(self.label_total_savings)
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)
        
        # Transaction Form Section
        form_group = QGroupBox("Post New Transaction")
        form_font = QFont("Arial", 10)
        form_font.setBold(True)
        form_group.setFont(form_font)
        form_layout = QFormLayout()
        
        # Amount input
        self.input_amount = QDoubleSpinBox()
        self.input_amount.setRange(0, 1_000_000)
        self.input_amount.setValue(0)
        self.input_amount.setDecimals(2)
        self.input_amount.setSingleStep(100)
        self.input_amount.setPrefix("₦")
        form_layout.addRow("Amount:", self.input_amount)
        
        # Transaction type
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Lodgment", "Deduction"])
        form_layout.addRow("Type:", self.combo_type)
        
        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)
        
        # Post button
        button_layout = QHBoxLayout()
        self.btn_post = QPushButton("Post Saving")
        self.btn_post.setMinimumHeight(40)
        btn_font = QFont("Arial", 10)
        btn_font.setBold(True)
        self.btn_post.setFont(btn_font)
        self.btn_post.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #888888;
            }
        """)
        self.btn_post.clicked.connect(self.post_saving)
        self.btn_post.setEnabled(False)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_post, 0, Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(button_layout)
        
        # Savings History Table
        history_title = QLabel("Transaction History (Last 10)")
        history_font = QFont("Arial", 12)
        history_font.setBold(True)
        history_title.setFont(history_font)
        main_layout.addWidget(history_title)
        
        self.table_savings = QTableWidget()
        self.table_savings.setColumnCount(5)
        self.table_savings.setHorizontalHeaderLabels([
            "Date", "Type", "Amount", "Running Balance", "ID"
        ])
        self.table_savings.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_savings.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_savings.horizontalHeader().setStretchLastSection(True)
        self.table_savings.setColumnHidden(4, True)  # Hide ID column
        main_layout.addWidget(self.table_savings)
        
        self.setLayout(main_layout)
    
    def search_member(self) -> None:
        """Search for a member by staff number and load their info."""
        
        staff_number = self.input_search.text().strip()
        
        if not staff_number:
            QMessageBox.warning(self, "Invalid Input", "Please enter a staff number.")
            return
        
        # Search for member
        success, member = get_member_by_staff_number(self.db_path, staff_number)
        
        if not success or not member:
            QMessageBox.warning(self, "Not Found", f"No member found with staff number '{staff_number}'.")
            self.current_member_id = None
            self.current_member_name = None
            self.label_member_name.setText("Name: Not Selected")
            self.label_total_savings.setText("Total Savings: ₦0.00")
            self.table_savings.setRowCount(0)
            self.btn_post.setEnabled(False)
            return
        
        # Store member info
        self.current_member_id = member['member_id']
        self.current_member_name = member['full_name']
        
        # Update member info display
        self.label_member_name.setText(f"Name: {member['full_name']}")
        
        # Load and display savings
        self.load_savings_data()
        
        # Enable post button
        self.btn_post.setEnabled(True)
        
        QMessageBox.information(self, "Success", f"Member found: {member['full_name']}")
    
    def load_savings_data(self) -> None:
        """Load and display current savings balance for the member."""

        if not self.current_member_id:
            return

        try:
            success, total_savings = get_total_savings(self.db_path, self.current_member_id)
            if not success:
                QMessageBox.critical(self, "Error", "Failed to load savings data.")
                return

            history_ok, history = get_member_savings(self.db_path, self.current_member_id)
            if not history_ok:
                QMessageBox.critical(self, "Error", "Failed to load savings history.")
                return

            self.table_savings.setRowCount(0)
            for row_idx, item in enumerate(history):
                self.table_savings.insertRow(row_idx)

                date_item = QTableWidgetItem(str(item.get('trans_date', '')))
                type_item = QTableWidgetItem(str(item.get('trans_type', '')))
                amount_item = QTableWidgetItem(f"₦{float(item.get('amount', 0.0)):,.2f}")
                balance_item = QTableWidgetItem(f"₦{float(item.get('running_balance', 0.0)):,.2f}")
                id_item = QTableWidgetItem(str(item.get('id', '')))

                self.table_savings.setItem(row_idx, 0, date_item)
                self.table_savings.setItem(row_idx, 1, type_item)
                self.table_savings.setItem(row_idx, 2, amount_item)
                self.table_savings.setItem(row_idx, 3, balance_item)
                self.table_savings.setItem(row_idx, 4, id_item)

            self.label_total_savings.setText(f"Total Savings: ₦{total_savings:,.2f}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load savings: {str(e)}")
    
    def post_saving(self) -> None:
        """Post a new savings transaction."""
        
        if not self.current_member_id:
            QMessageBox.warning(self, "Error", "Please select a member first.")
            return
        
        amount = self.input_amount.value()
        trans_type = self.combo_type.currentText()
        
        if amount <= 0:
            QMessageBox.warning(self, "Invalid Input", "Amount must be greater than 0.")
            return
        
        # Add saving to database
        success, message = add_saving(self.db_path, self.current_member_id, amount, trans_type)
        
        if success:
            QMessageBox.information(self, "Success", message)
            # Clear amount field
            self.input_amount.setValue(0)
            # Refresh savings history
            self.load_savings_data()
        else:
            QMessageBox.critical(self, "Error", message)

    def clear_selection(self) -> None:
        """Clear the active member context and reset UI widgets."""
        self.current_member_id = None
        self.current_member_name = None
        self.input_search.clear()
        self.input_amount.setValue(0)
        self.label_member_name.setText("Name: Not Selected")
        self.label_total_savings.setText("Total Savings: ₦0.00")
        self.table_savings.setRowCount(0)
        self.btn_post.setEnabled(False)


class LoansPage(QWidget):
    """Page for Loans management with eligibility checking, application, and schedule preview."""
    
    def __init__(self, db_path: str = "swiftledger.db"):
        super().__init__()
        self.db_path = db_path
        self.current_member_id = None
        self.current_member_name = None
        self.max_eligible_amount = 0.0
        self.total_savings = 0.0
        self.loan_multiplier = 2.0
        self.default_interest_rate = 12.0
        self.default_duration = 24
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Title
        title = QLabel("Loan Management")
        title_font = QFont("Arial", 18)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)
        
        # Search Section
        search_group = QGroupBox("Find Member")
        search_font = QFont("Arial", 10)
        search_font.setBold(True)
        search_group.setFont(search_font)
        search_layout = QHBoxLayout()
        
        search_label = QLabel("Staff Number:")
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("e.g., EMP001")
        self.btn_search = QPushButton("Search")
        self.btn_search.setMinimumWidth(100)
        self.btn_search.clicked.connect(self.search_member)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.input_search)
        search_layout.addWidget(self.btn_search)
        search_layout.addStretch()
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)
        
        # Eligibility Section
        eligibility_group = QGroupBox("Eligibility Information")
        eligibility_font = QFont("Arial", 10)
        eligibility_font.setBold(True)
        eligibility_group.setFont(eligibility_font)
        eligibility_layout = QHBoxLayout()
        
        self.label_member_name = QLabel("Member: Not Selected")
        self.label_member_name.setFont(QFont("Arial", 11))
        
        self.label_total_savings = QLabel("Total Savings: ₦0.00")
        self.label_total_savings.setFont(QFont("Arial", 11))
        
        self.label_max_eligible = QLabel("Max Eligible Loan: ₦0.00")
        max_eligible_font = QFont("Arial", 11)
        max_eligible_font.setBold(True)
        self.label_max_eligible.setFont(max_eligible_font)
        
        eligibility_layout.addWidget(self.label_member_name)
        eligibility_layout.addStretch()
        eligibility_layout.addWidget(self.label_total_savings)
        eligibility_layout.addStretch()
        eligibility_layout.addWidget(self.label_max_eligible)
        eligibility_group.setLayout(eligibility_layout)
        main_layout.addWidget(eligibility_group)
        
        # Loan Application Form
        form_group = QGroupBox("Loan Application")
        form_font = QFont("Arial", 10)
        form_font.setBold(True)
        form_group.setFont(form_font)
        form_layout = QFormLayout()
        
        # Principal input
        self.input_principal = QDoubleSpinBox()
        self.input_principal.setRange(0, 10_000_000)
        self.input_principal.setValue(0)
        self.input_principal.setDecimals(2)
        self.input_principal.setSingleStep(1000)
        self.input_principal.setPrefix("₦")
        self.input_principal.valueChanged.connect(self.validate_principal)
        form_layout.addRow("Requested Principal:", self.input_principal)
        
        # Interest rate input
        self.input_interest_rate = QDoubleSpinBox()
        self.input_interest_rate.setRange(0, 100)
        self.input_interest_rate.setValue(self.default_interest_rate)
        self.input_interest_rate.setDecimals(2)
        self.input_interest_rate.setSingleStep(0.5)
        self.input_interest_rate.setSuffix("%")
        form_layout.addRow("Annual Interest Rate:", self.input_interest_rate)
        
        # Duration input
        self.input_duration = QSpinBox()
        self.input_duration.setRange(1, 60)
        self.input_duration.setValue(self.default_duration)
        self.input_duration.setSuffix(" months")
        form_layout.addRow("Duration:", self.input_duration)
        
        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)
        
        # Validation and Preview Section
        button_layout = QHBoxLayout()
        
        self.btn_validate = QPushButton("Validate Loan")
        self.btn_validate.setMinimumHeight(40)
        btn_font = QFont("Arial", 10)
        btn_font.setBold(True)
        self.btn_validate.setFont(btn_font)
        self.btn_validate.clicked.connect(self.validate_loan)
        self.btn_validate.setEnabled(False)
        button_layout.addWidget(self.btn_validate)
        
        self.btn_preview = QPushButton("Preview Schedule")
        self.btn_preview.setMinimumHeight(40)
        self.btn_preview.setFont(btn_font)
        self.btn_preview.clicked.connect(self.show_schedule_preview)
        self.btn_preview.setEnabled(False)
        button_layout.addWidget(self.btn_preview)
        
        button_layout.addStretch()
        
        self.btn_submit = QPushButton("Submit Loan")
        self.btn_submit.setMinimumHeight(40)
        self.btn_submit.setFont(btn_font)
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover:!disabled {
                background-color: #2ecc71;
            }
            QPushButton:pressed:!disabled {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #888888;
                color: #cccccc;
            }
        """)
        self.btn_submit.clicked.connect(self.submit_loan)
        self.btn_submit.setEnabled(False)
        button_layout.addWidget(self.btn_submit)
        
        main_layout.addLayout(button_layout)
        
        # Validation Status Label
        self.label_validation_status = QLabel("")
        self.label_validation_status.setFont(QFont("Arial", 9))
        main_layout.addWidget(self.label_validation_status)
        
        # Active Loans Table
        loans_title = QLabel("Active Loans")
        loans_font = QFont("Arial", 12)
        loans_font.setBold(True)
        loans_title.setFont(loans_font)
        main_layout.addWidget(loans_title)
        
        self.table_loans = QTableWidget()
        self.table_loans.setColumnCount(5)
        self.table_loans.setHorizontalHeaderLabels([
            "Loan ID", "Principal", "Interest Rate", "Status", "Date Issued"
        ])
        self.table_loans.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_loans.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_loans.horizontalHeader().setStretchLastSection(True)
        main_layout.addWidget(self.table_loans)
        
        self.setLayout(main_layout)
        
        # Load system settings
        self.load_system_settings()
    
    def load_system_settings(self) -> None:
        """Load system settings for loan defaults."""
        ok, settings = get_system_settings(self.db_path)
        if ok and settings:
            self.loan_multiplier = float(settings.get('loan_multiplier', 2.0))
            self.default_interest_rate = float(settings.get('default_interest_rate', 12.0))
            self.default_duration = int(settings.get('default_duration', 24))
            self.input_interest_rate.setValue(self.default_interest_rate)
            self.input_duration.setValue(self.default_duration)
    
    def search_member(self) -> None:
        """Search for a member by staff number."""
        staff_number = self.input_search.text().strip()
        
        if not staff_number:
            QMessageBox.warning(self, "Invalid Input", "Please enter a staff number.")
            return

        success, member = get_member_by_staff_number(self.db_path, staff_number)

        if not success or not member:
            QMessageBox.warning(self, "Not Found", f"No member found with staff number '{staff_number}'.")
            self.current_member_id = None
            self.current_member_name = None
            self.label_member_name.setText("Member: Not Selected")
            self.label_total_savings.setText("Total Savings: ₦0.00")
            self.label_max_eligible.setText("Max Eligible Loan: ₦0.00")
            self.table_loans.setRowCount(0)
            self.btn_validate.setEnabled(False)
            self.btn_preview.setEnabled(False)
            self.btn_submit.setEnabled(False)
            return
        
        self.current_member_id = member['member_id']
        self.current_member_name = member['full_name']
        
        # Get total savings
        ok, total_savings = get_total_savings(self.db_path, self.current_member_id)
        if ok:
            self.total_savings = total_savings
        else:
            self.total_savings = 0.0
        
        # Update display
        self.max_eligible_amount = self.loan_multiplier * self.total_savings
        self.label_member_name.setText(f"Member: {self.current_member_name}")
        self.label_total_savings.setText(f"Total Savings: ₦{self.total_savings:,.2f}")
        self.label_max_eligible.setText(f"Max Eligible Loan: ₦{self.max_eligible_amount:,.2f}")
        
        # Load active loans
        self.load_active_loans()
        
        # Enable validation and preview buttons
        self.btn_validate.setEnabled(True)
        self.btn_preview.setEnabled(True)
        
        # Clear validation status
        self.label_validation_status.setText("")
    
    def validate_principal(self) -> None:
        """Real-time validation as principal amount changes."""
        principal = self.input_principal.value()
        
        if self.current_member_id is None:
            return
        
        if principal > self.max_eligible_amount:
            self.btn_submit.setEnabled(False)
            self.label_validation_status.setText(
                f"❌ Principal exceeds limit (Max: ₦{self.max_eligible_amount:,.2f})"
            )
        elif principal <= 0:
            self.btn_submit.setEnabled(False)
            self.label_validation_status.setText("❌ Principal must be greater than 0")
        else:
            self.btn_submit.setEnabled(True)
            self.label_validation_status.setText(f"✓ Principal is within eligibility limit")
    
    def validate_loan(self) -> None:
        """Explicitly validate the loan application."""
        if self.current_member_id is None:
            QMessageBox.warning(self, "Error", "Please search for a member first.")
            return
        
        principal = self.input_principal.value()
        
        if principal <= 0:
            QMessageBox.warning(self, "Invalid Principal", "Principal must be greater than 0.")
            return
        
        if principal > self.max_eligible_amount:
            QMessageBox.warning(
                self,
                "Exceeds Limit",
                f"Requested principal (₦{principal:,.2f}) exceeds maximum eligibility (₦{self.max_eligible_amount:,.2f})."
            )
            return
        
        QMessageBox.information(self, "Valid", "✓ Loan application is valid and ready to submit.")
    
    def show_schedule_preview(self) -> None:
        """Show a preview of the repayment schedule."""
        if self.current_member_id is None:
            QMessageBox.warning(self, "Error", "Please search for a member first.")
            return
        
        principal = self.input_principal.value()
        interest_rate = self.input_interest_rate.value()
        duration = self.input_duration.value()
        
        if principal <= 0:
            QMessageBox.warning(self, "Invalid Principal", "Principal must be greater than 0.")
            return
        
        # Calculate schedule
        schedule = calculate_repayment_schedule(principal, interest_rate, duration)
        
        # Create preview dialog
        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle("Repayment Schedule Preview")
        preview_dialog.setGeometry(100, 100, 900, 600)
        
        layout = QVBoxLayout(preview_dialog)
        
        # Info label
        info_text = f"Loan: ₦{principal:,.2f} @ {interest_rate}% for {duration} months"
        info_label = QLabel(info_text)
        info_font = QFont("Arial", 11)
        info_font.setBold(True)
        info_label.setFont(info_font)
        layout.addWidget(info_label)
        
        # Schedule table
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Month", "Principal", "Interest", "Total", "Remaining"])
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        for row_idx, month_data in enumerate(schedule):
            table.insertRow(row_idx)
            
            month_item = QTableWidgetItem(str(month_data['month_number']))
            table.setItem(row_idx, 0, month_item)
            
            principal_item = QTableWidgetItem(f"₦{month_data['principal_payment']:,.2f}")
            principal_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            table.setItem(row_idx, 1, principal_item)
            
            interest_item = QTableWidgetItem(f"₦{month_data['interest_payment']:,.2f}")
            interest_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            table.setItem(row_idx, 2, interest_item)
            
            total_item = QTableWidgetItem(f"₦{month_data['total_payment']:,.2f}")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            table.setItem(row_idx, 3, total_item)
            
            remaining_item = QTableWidgetItem(f"₦{month_data['remaining_balance']:,.2f}")
            remaining_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            table.setItem(row_idx, 4, remaining_item)
        
        layout.addWidget(table)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(preview_dialog.accept)
        layout.addWidget(close_btn)
        
        preview_dialog.exec()
    
    def submit_loan(self) -> None:
        """Submit the loan application."""
        if self.current_member_id is None:
            QMessageBox.warning(self, "Error", "Please search for a member first.")
            return
        
        principal = self.input_principal.value()
        interest_rate = self.input_interest_rate.value()
        duration = self.input_duration.value()
        
        if principal <= 0:
            QMessageBox.warning(self, "Invalid Principal", "Principal must be greater than 0.")
            return
        
        # Apply for loan
        success, message = apply_for_loan(self.db_path, self.current_member_id, principal, interest_rate, duration)
        
        if success:
            QMessageBox.information(self, "Success", message)
            # Clear form
            self.input_principal.setValue(0)
            self.input_interest_rate.setValue(self.default_interest_rate)
            self.input_duration.setValue(self.default_duration)
            # Reload active loans
            self.load_active_loans()
            # Reset validation status
            self.label_validation_status.setText("")
        else:
            QMessageBox.critical(self, "Error", message)
    
    def load_active_loans(self) -> None:
        """Load and display active loans for the current member."""
        if self.current_member_id is None:
            self.table_loans.setRowCount(0)
            return
        
        try:
            success, loans = get_member_loans(self.db_path, self.current_member_id)
            
            if not success:
                QMessageBox.critical(self, "Error", "Failed to load loans.")
                return
            
            # Clear table
            self.table_loans.setRowCount(0)
            
            # Populate table
            for row_idx, loan in enumerate(loans):
                self.table_loans.insertRow(row_idx)
                
                # Loan ID
                loan_id_item = QTableWidgetItem(str(loan['loan_id']))
                self.table_loans.setItem(row_idx, 0, loan_id_item)
                
                # Principal
                principal_item = QTableWidgetItem(f"₦{loan['principal']:,.2f}")
                principal_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                self.table_loans.setItem(row_idx, 1, principal_item)
                
                # Interest Rate
                rate_item = QTableWidgetItem(f"{loan['interest_rate']:.2f}%")
                rate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_loans.setItem(row_idx, 2, rate_item)
                
                # Status
                status = loan['status']
                status_item = QTableWidgetItem(status)
                if status == 'Active':
                    status_item.setForeground(Qt.GlobalColor.green)
                elif status == 'Closed':
                    status_item.setForeground(Qt.GlobalColor.blue)
                elif status == 'Default':
                    status_item.setForeground(Qt.GlobalColor.red)
                self.table_loans.setItem(row_idx, 3, status_item)
                
                # Date Issued
                date_item = QTableWidgetItem(str(loan['date_issued']))
                self.table_loans.setItem(row_idx, 4, date_item)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load loans: {str(e)}")

    def clear_selection(self) -> None:
        """Clear the active member context and reset UI widgets."""
        self.current_member_id = None
        self.current_member_name = None
        self.total_savings = 0.0
        self.max_eligible_amount = 0.0
        self.input_search.clear()
        self.input_principal.setValue(0)
        self.input_interest_rate.setValue(self.default_interest_rate)
        self.input_duration.setValue(self.default_duration)
        self.label_member_name.setText("Member: Not Selected")
        self.label_total_savings.setText("Total Savings: ₦0.00")
        self.label_max_eligible.setText("Max Eligible Loan: ₦0.00")
        self.label_validation_status.setText("")
        self.table_loans.setRowCount(0)
        self.btn_validate.setEnabled(False)
        self.btn_preview.setEnabled(False)
        self.btn_submit.setEnabled(False)


class MainWindow(QMainWindow):
    """Main application window for SwiftLedger."""
    
    def __init__(self, db_path: str = "swiftledger.db"):
        super().__init__()
        self.db_path = db_path
        self.last_interaction_time = time.time()
        self.is_locked = False
        self.setWindowTitle("SwiftLedger - Thrift Society Management")
        self.setGeometry(100, 100, 1200, 700)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout (horizontal: sidebar + content)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create sidebar
        self.sidebar = self.create_sidebar()
        main_layout.addWidget(self.sidebar)
        
        # Create stacked widget for pages
        self.stacked_widget = QStackedWidget()
        self.create_pages()
        main_layout.addWidget(self.stacked_widget)
        
        # Apply stylesheet
        self.apply_stylesheet()

        QApplication.instance().installEventFilter(self)
        self._start_watchdog_timer()

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress):
            self.last_interaction_time = time.time()
        return super().eventFilter(obj, event)

    def _start_watchdog_timer(self) -> None:
        self.watchdog_timer = QTimer(self)
        self.watchdog_timer.setInterval(5_000)
        self.watchdog_timer.timeout.connect(self._check_inactivity)
        self.watchdog_timer.start()

    def _check_inactivity(self) -> None:
        if self.is_locked:
            return
        # Read timeout from settings (default 10 min)
        ok, settings = get_system_settings(self.db_path)
        timeout = int(settings.get('timeout_minutes', 10)) * 60 if ok and settings else 600
        if time.time() - self.last_interaction_time > timeout:
            self.lock_screen()

    def _clear_sensitive_state(self) -> None:
        if hasattr(self, "savings_page"):
            self.savings_page.clear_selection()
        if hasattr(self, "loans_page"):
            self.loans_page.clear_selection()

    def lock_screen(self) -> None:
        self.is_locked = True
        self._clear_sensitive_state()

        dialog = QDialog(self)
        dialog.setWindowTitle("Session Locked")
        dialog.setModal(True)
        dialog.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        dialog.setFixedSize(420, 360)

        layout = QVBoxLayout(dialog)
        login = LoginScreen(self.db_path)
        login.login_successful.connect(dialog.accept)
        layout.addWidget(login)

        dialog.exec()
        self.last_interaction_time = time.time()
        self.is_locked = False
    
    def create_sidebar(self) -> QFrame:
        """Create the left sidebar with navigation buttons."""
        
        sidebar = QFrame()
        sidebar.setMinimumWidth(200)
        sidebar.setMaximumWidth(200)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("SwiftLedger")
        title_font = QFont("Arial", 14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)
        
        # Navigation buttons
        self.btn_dashboard = QPushButton("Dashboard")
        self.btn_members = QPushButton("Members")
        self.btn_savings = QPushButton("Savings")
        self.btn_loans = QPushButton("Loans")
        self.btn_audit = QPushButton("Audit Logs")
        self.btn_settings = QPushButton("Settings")
        self.btn_about = QPushButton("About")
        
        buttons = [
            self.btn_dashboard,
            self.btn_members,
            self.btn_savings,
            self.btn_loans,
            self.btn_audit,
            self.btn_settings,
            self.btn_about,
        ]
        
        for i, button in enumerate(buttons):
            button.setMinimumHeight(45)
            button.setFont(QFont("Arial", 10))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked, idx=i: self.navigate_to_page(idx))
            layout.addWidget(button)
        
        # Add stretch to push buttons to the top
        layout.addStretch()
        
        return sidebar
    
    def create_pages(self) -> None:
        """Create placeholder pages and add them to the stacked widget."""
        
        self.dashboard_page = DashboardPage(self.db_path)
        self.members_page = MembersPage(self.db_path)
        self.savings_page = SavingsPage(self.db_path)
        self.loans_page = LoansPage(self.db_path)
        self.audit_page = AuditLogPage(self.db_path)
        self.settings_page = SettingsPage(self.db_path)
        self.about_page = AboutPage(self.db_path)
        
        self.stacked_widget.addWidget(self.dashboard_page)
        self.stacked_widget.addWidget(self.members_page)
        self.stacked_widget.addWidget(self.savings_page)
        self.stacked_widget.addWidget(self.loans_page)
        self.stacked_widget.addWidget(self.audit_page)
        self.stacked_widget.addWidget(self.settings_page)
        self.stacked_widget.addWidget(self.about_page)
        
        # Set default page
        self.stacked_widget.setCurrentIndex(0)
        self.dashboard_page.refresh_dashboard()
    
    def navigate_to_page(self, page_index: int) -> None:
        """Navigate to a specific page in the stacked widget."""
        self.stacked_widget.setCurrentIndex(page_index)
        self.update_button_styles(page_index)
        # Auto-refresh dashboard whenever it becomes visible
        if page_index == 0:
            self.dashboard_page.refresh_dashboard()
        elif page_index == 4:
            self.audit_page.refresh_logs()
    
    def update_button_styles(self, active_index: int) -> None:
        """Update button styles to highlight the active button."""
        
        buttons = [
            self.btn_dashboard,
            self.btn_members,
            self.btn_savings,
            self.btn_loans,
            self.btn_audit,
            self.btn_settings,
            self.btn_about,
        ]
        
        for i, button in enumerate(buttons):
            if i == active_index:
                button.setProperty("active", True)
            else:
                button.setProperty("active", False)
            
            # Re-apply stylesheet to update the button
            button.style().unpolish(button)
            button.style().polish(button)
    
    def apply_stylesheet(self) -> None:
        """Apply the high-contrast dark theme to the application."""
        stylesheet = """
            /* 1. The Main Foundation */
            QMainWindow, QStackedWidget, QWidget {
                background-color: #1e1e1e;
                color: #ecf0f1;
            }

            /* 2. The Sidebar */
            QFrame#sidebar {
                background-color: #2c3e50;
                border-right: 1px solid #34495e;
            }

            /* 3. Text & Labels */
            QLabel {
                color: #ffffff;
                font-size: 14px;
            }

            /* 4. Input Fields (The fix for your visibility bug!) */
            QLineEdit, QComboBox, QDateEdit {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 3px;
            }

            /* 5. Tables */
            QTableWidget {
                background-color: #252525;
                color: #ecf0f1;
                gridline-color: #333333;
            }
            
            /* 6. Success Button */
            QPushButton#register_btn {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
            }
        """
        self.setStyleSheet(stylesheet)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
