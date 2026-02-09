"""
Main application window for SwiftLedger.
Contains the sidebar navigation and stacked widget for multiple pages.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame, 
    QPushButton, QStackedWidget, QLabel, QGroupBox, QFormLayout,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem, QMessageBox,
    QAbstractItemView, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont
from datetime import date
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.queries import (
    add_member, get_all_members, get_member_by_staff_number, 
    add_saving, get_member_savings
)


class DashboardPage(QWidget):
    """Placeholder page for Dashboard."""
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("Dashboard Page")
        font = QFont("Arial", 18)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label)
        layout.addStretch()
        self.setLayout(layout)


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
        
        # Department dropdown
        self.combo_department = QComboBox()
        self.combo_department.addItems([
            "Admin", "Science", "Engineering", "Finance", 
            "Marketing", "HR", "Operations", "Other"
        ])
        form_layout.addRow("Department:", self.combo_department)
        
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
            "Staff Number", "Full Name", "Department", "Date Joined", "Status"
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
        department = self.combo_department.currentText()
        
        if not staff_number or not full_name:
            QMessageBox.warning(self, "Invalid Input", "Please fill in all required fields.")
            return
        
        # Prepare member data
        member_data = {
            'staff_number': staff_number,
            'full_name': full_name,
            'date_joined': str(date.today())
        }
        
        # Add member to database
        success, message = add_member(self.db_path, member_data)
        
        if success:
            QMessageBox.information(self, "Success", message)
            # Clear inputs
            self.input_staff_number.clear()
            self.input_full_name.clear()
            self.combo_department.setCurrentIndex(0)
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
                
                # Department (placeholder - not stored in DB yet)
                dept_item = QTableWidgetItem("N/A")
                self.table_members.setItem(row_idx, 2, dept_item)
                
                # Date Joined
                date_joined = member.get('date_joined', 'N/A')
                date_item = QTableWidgetItem(str(date_joined))
                self.table_members.setItem(row_idx, 3, date_item)
                
                # Status (placeholder)
                status_item = QTableWidgetItem("Active")
                self.table_members.setItem(row_idx, 4, status_item)
        
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
        """Load and display savings data for the current member."""
        
        if not self.current_member_id:
            return
        
        try:
            # Get all savings records for the member
            success, savings = get_member_savings(self.db_path, self.current_member_id)
            
            if not success:
                QMessageBox.critical(self, "Error", "Failed to load savings data.")
                return
            
            # Clear table
            self.table_savings.setRowCount(0)
            
            # Calculate total and running balance
            total_savings = 0.0
            running_balance = 0.0
            limited_savings = savings[:10]  # Last 10 transactions
            
            # Populate table in reverse order (oldest first for running balance calculation)
            for savings_record in reversed(limited_savings):
                amount = float(savings_record['amount'])
                trans_type = savings_record['type']
                
                # Calculate running balance
                if trans_type == 'Lodgment':
                    running_balance += amount
                    total_savings += amount
                else:  # Deduction
                    running_balance -= amount
                    total_savings -= amount
            
            # Now add rows in chronological order (newest first for display)
            for row_idx, savings_record in enumerate(limited_savings):
                self.table_savings.insertRow(row_idx)
                
                # Date
                date_item = QTableWidgetItem(str(savings_record['date']))
                self.table_savings.setItem(row_idx, 0, date_item)
                
                # Type with color coding
                trans_type = savings_record['type']
                type_item = QTableWidgetItem(trans_type)
                if trans_type == 'Lodgment':
                    type_item.setForeground(Qt.GlobalColor.green)
                else:
                    type_item.setForeground(Qt.GlobalColor.red)
                self.table_savings.setItem(row_idx, 1, type_item)
                
                # Amount
                amount = float(savings_record['amount'])
                amount_item = QTableWidgetItem(f"₦{amount:,.2f}")
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                self.table_savings.setItem(row_idx, 2, amount_item)
                
                # Running balance (placeholder - you may need to recalculate)
                balance_item = QTableWidgetItem(f"₦{running_balance:,.2f}")
                balance_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                self.table_savings.setItem(row_idx, 3, balance_item)
                
                # ID (hidden)
                id_item = QTableWidgetItem(str(savings_record['savings_id']))
                self.table_savings.setItem(row_idx, 4, id_item)
            
            # Update total savings display
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


class LoansPage(QWidget):
    """Placeholder page for Loans management."""
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("Loans Page")
        font = QFont("Arial", 18)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label)
        layout.addStretch()
        self.setLayout(layout)


class MainWindow(QMainWindow):
    """Main application window for SwiftLedger."""
    
    def __init__(self, db_path: str = "swiftledger.db"):
        super().__init__()
        self.db_path = db_path
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
        
        buttons = [
            self.btn_dashboard,
            self.btn_members,
            self.btn_savings,
            self.btn_loans
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
        
        self.dashboard_page = DashboardPage()
        self.members_page = MembersPage(self.db_path)
        self.savings_page = SavingsPage(self.db_path)
        self.loans_page = LoansPage()
        
        self.stacked_widget.addWidget(self.dashboard_page)
        self.stacked_widget.addWidget(self.members_page)
        self.stacked_widget.addWidget(self.savings_page)
        self.stacked_widget.addWidget(self.loans_page)
        
        # Set default page
        self.stacked_widget.setCurrentIndex(0)
    
    def navigate_to_page(self, page_index: int) -> None:
        """Navigate to a specific page in the stacked widget."""
        self.stacked_widget.setCurrentIndex(page_index)
        self.update_button_styles(page_index)
    
    def update_button_styles(self, active_index: int) -> None:
        """Update button styles to highlight the active button."""
        
        buttons = [
            self.btn_dashboard,
            self.btn_members,
            self.btn_savings,
            self.btn_loans
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
