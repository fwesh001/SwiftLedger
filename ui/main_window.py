"""
Main application window for SwiftLedger.
Contains the sidebar navigation and stacked widget for multiple pages.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame, 
    QPushButton, QStackedWidget, QLabel, QGroupBox, QFormLayout,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem, QMessageBox
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
        label.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(label)
        layout.addStretch()
        self.setLayout(layout)


class MembersPage(QWidget):
    """Placeholder page for Members management."""
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("Members Page")
        label.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(label)
        layout.addStretch()
        self.setLayout(layout)


class SavingsPage(QWidget):
    """Placeholder page for Savings management."""
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("Savings Page")
        label.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(label)
        layout.addStretch()
        self.setLayout(layout)


class LoansPage(QWidget):
    """Placeholder page for Loans management."""
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("Loans Page")
        label.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(label)
        layout.addStretch()
        self.setLayout(layout)


class MainWindow(QMainWindow):
    """Main application window for SwiftLedger."""
    
    def __init__(self):
        super().__init__()
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
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
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
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked, idx=i: self.navigate_to_page(idx))
            layout.addWidget(button)
        
        # Add stretch to push buttons to the top
        layout.addStretch()
        
        return sidebar
    
    def create_pages(self) -> None:
        """Create placeholder pages and add them to the stacked widget."""
        
        self.dashboard_page = DashboardPage()
        self.members_page = MembersPage()
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
        """Apply dark theme stylesheet to the application."""
        
        stylesheet = """
            QMainWindow {
                background-color: #f5f5f5;
            }
            
            QFrame {
                background-color: #2c3e50;
                border: none;
            }
            
            QLabel {
                color: white;
            }
            
            QPushButton {
                background-color: #34495e;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
                transition: background-color 0.3s;
            }
            
            QPushButton:hover {
                background-color: #3d5a72;
            }
            
            QPushButton:pressed {
                background-color: #2c3e50;
            }
            
            QPushButton[active="true"] {
                background-color: #3498db;
                border-left: 4px solid #2980b9;
            }
            
            QPushButton[active="true"]:hover {
                background-color: #5dade2;
            }
            
            QStackedWidget {
                background-color: #ecf0f1;
            }
            
            QWidget {
                background-color: #ecf0f1;
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
