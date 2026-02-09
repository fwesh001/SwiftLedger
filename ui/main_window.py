"""
Main application window for SwiftLedger.
Contains the sidebar navigation and stacked widget for multiple pages.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame, 
    QPushButton, QStackedWidget, QLabel, QGroupBox, QFormLayout,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem, QMessageBox,
    QAbstractItemView
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont
from datetime import date
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.queries import add_member, get_all_members


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
    """Placeholder page for Savings management."""
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("Savings Page")
        font = QFont("Arial", 18)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label)
        layout.addStretch()
        self.setLayout(layout)


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
        self.savings_page = SavingsPage()
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
