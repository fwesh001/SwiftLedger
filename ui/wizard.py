"""
First-run wizard for SwiftLedger initial setup.

Guides users through welcome, identity setup, security configuration,
and system finalization steps.
"""

import sys
from pathlib import Path
from typing import cast

from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_init import init_db, save_settings, log_event
from security import hash_credential


# ──────────────────────────────────────────────────────────────────────────────
# Step 1: Welcome Page
# ──────────────────────────────────────────────────────────────────────────────


class WelcomePage(QWizardPage):
    """Welcome page with branding and initial greeting."""

    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to SwiftLedger")
        self.setSubTitle("Initialize your savings and loan management system")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Main welcome message
        welcome_label = QLabel("Welcome to SwiftLedger")
        welcome_font = QFont()
        welcome_font.setPointSize(24)
        welcome_font.setBold(True)
        welcome_label.setFont(welcome_font)
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome_label)

        # Descriptive text
        description = QLabel(
            "This wizard will guide you through the initial setup of SwiftLedger,\n"
            "including organization information, security settings, and system configuration."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        layout.addWidget(description)

        # Spacer
        layout.addStretch()

        # Footer with developer credit
        footer = QLabel("Designed and Developed by Zabdiel")
        footer_font = QFont()
        footer_font.setPointSize(10)
        footer_font.setItalic(True)
        footer.setFont(footer_font)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)


# ──────────────────────────────────────────────────────────────────────────────
# Step 2: Identity Page
# ──────────────────────────────────────────────────────────────────────────────


class IdentityPage(QWizardPage):
    """Organization identity and contact information form."""

    def __init__(self):
        super().__init__()
        self.setTitle("Organization Identity")
        self.setSubTitle("Enter your organization's details")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Society Name
        society_label = QLabel("Society Name:")
        self.society_input = QLineEdit()
        self.society_input.setPlaceholderText("e.g., Main Street Savings Society")
        layout.addWidget(society_label)
        layout.addWidget(self.society_input)

        # Street
        street_label = QLabel("Street:")
        self.street_input = QLineEdit()
        self.street_input.setPlaceholderText("e.g., 123 Main Street")
        layout.addWidget(street_label)
        layout.addWidget(self.street_input)

        # City/State
        city_label = QLabel("City/State:")
        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("e.g., New York, NY")
        layout.addWidget(city_label)
        layout.addWidget(self.city_input)

        # Phone
        phone_label = QLabel("Phone:")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("e.g., +1 (555) 123-4567")
        layout.addWidget(phone_label)
        layout.addWidget(self.phone_input)

        # Email
        email_label = QLabel("Email:")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("e.g., contact@society.com")
        layout.addWidget(email_label)
        layout.addWidget(self.email_input)

        # Registration Number
        reg_label = QLabel("Registration Number:")
        self.reg_input = QLineEdit()
        self.reg_input.setPlaceholderText("e.g., REG-2024-001")
        layout.addWidget(reg_label)
        layout.addWidget(self.reg_input)

        layout.addStretch()

    def get_data(self) -> dict:
        """Return form data as a dictionary."""
        return {
            "society_name": self.society_input.text(),
            "street": self.street_input.text(),
            "city_state": self.city_input.text(),
            "phone": self.phone_input.text(),
            "email": self.email_input.text(),
            "reg_no": self.reg_input.text(),
        }

    def validatePage(self) -> bool:
        """Validate that required fields are filled."""
        data = self.get_data()
        required_fields = ["society_name", "phone", "email"]
        
        for field in required_fields:
            if not data[field].strip():
                QMessageBox.warning(
                    self,
                    "Missing Information",
                    f"Please enter a valid {field.replace('_', ' ').title()}."
                )
                return False
        return True


# ──────────────────────────────────────────────────────────────────────────────
# Step 3: Security Page
# ──────────────────────────────────────────────────────────────────────────────


class SecurityPage(QWizardPage):
    """Security mode selection and credential setup."""

    def __init__(self):
        super().__init__()
        self.setTitle("Security Configuration")
        self.setSubTitle("Choose your security mode and set your credentials")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Security mode selection
        mode_label = QLabel("Security Mode:")
        mode_font = QFont()
        mode_font.setBold(True)
        mode_label.setFont(mode_font)
        layout.addWidget(mode_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "PIN (4-6 digits)",
            "Password (text)",
            "System Authentication (Windows Hello)"
        ])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        layout.addWidget(self.mode_combo)

        layout.addSpacing(20)

        # Credential input (hidden for System Auth)
        self.credential_label = QLabel("Enter your PIN/Password:")
        self.credential_label.setFont(mode_font)
        layout.addWidget(self.credential_label)

        self.credential_input = QLineEdit()
        self.credential_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.credential_input.setPlaceholderText("Leave empty for System Authentication")
        layout.addWidget(self.credential_input)

        # Confirm credential
        self.confirm_label = QLabel("Confirm PIN/Password:")
        self.confirm_label.setFont(mode_font)
        layout.addWidget(self.confirm_label)

        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.confirm_input)

        # Info message
        info_label = QLabel(
            "For System Authentication, Windows Hello or system login will be used.\n"
            "For PIN/Password, you'll need to set a secure code above."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        layout.addWidget(info_label)

        layout.addStretch()

        # Initial state
        self._on_mode_changed()

    def _on_mode_changed(self) -> None:
        """Update visibility of credential fields based on selected mode."""
        is_system_auth = "System Authentication" in self.mode_combo.currentText()
        
        self.credential_label.setVisible(not is_system_auth)
        self.credential_input.setVisible(not is_system_auth)
        self.confirm_label.setVisible(not is_system_auth)
        self.confirm_input.setVisible(not is_system_auth)

    def get_security_mode(self) -> str:
        """Return the selected security mode."""
        mode_text = self.mode_combo.currentText()
        if "PIN" in mode_text:
            return "PIN"
        elif "Password" in mode_text:
            return "Password"
        else:
            return "System Auth"

    def get_credential(self) -> str:
        """Return the entered credential or empty string for System Auth."""
        if self.get_security_mode() == "System Auth":
            return ""
        return self.credential_input.text()

    def validatePage(self) -> bool:
        """Validate security configuration."""
        mode = self.get_security_mode()
        
        if mode == "System Auth":
            return True
        
        # Validate PIN/Password
        credential = self.get_credential()
        confirm = self.confirm_input.text()

        if not credential or not confirm:
            QMessageBox.warning(
                self,
                "Missing Credential",
                "Please enter and confirm your PIN/Password."
            )
            return False

        if credential != confirm:
            QMessageBox.warning(
                self,
                "Credential Mismatch",
                "PIN/Password entries do not match. Please try again."
            )
            self.credential_input.clear()
            self.confirm_input.clear()
            return False

        if mode == "PIN":
            if not credential.isdigit() or not (4 <= len(credential) <= 6):
                QMessageBox.warning(
                    self,
                    "Invalid PIN",
                    "PIN must be 4-6 digits."
                )
                return False

        return True


# ──────────────────────────────────────────────────────────────────────────────
# Step 4: Finalize Page
# ──────────────────────────────────────────────────────────────────────────────


class FinalizePage(QWizardPage):
    """Final confirmation and system initialization."""

    def __init__(self):
        super().__init__()
        self.setTitle("Initialization Complete")
        self.setSubTitle("Review and finalize your setup")
        self.setCommitPage(True)  # Mark as final step
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        summary_label = QLabel("Summary of Settings")
        summary_font = QFont()
        summary_font.setPointSize(12)
        summary_font.setBold(True)
        summary_label.setFont(summary_font)
        layout.addWidget(summary_label)

        # Summary text area
        self.summary_text = QLabel()
        self.summary_text.setWordWrap(True)
        self.summary_text.setStyleSheet("background-color: #ecf0f1; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.summary_text)

        layout.addSpacing(20)

        finish_label = QLabel(
            "Click 'Finish' to complete setup and launch SwiftLedger."
        )
        finish_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        layout.addWidget(finish_label)

        layout.addStretch()

    def initializePage(self) -> None:
        """Populate summary before showing this page."""
        wizard = cast(FirstRunWizard, self.wizard())
        identity_data = wizard.identity_page.get_data()
        security_mode = wizard.security_page.get_security_mode()

        summary = f"""
        <b>Organization Information:</b><br>
        Society Name: {identity_data['society_name']}<br>
        Street: {identity_data['street']}<br>
        City/State: {identity_data['city_state']}<br>
        Phone: {identity_data['phone']}<br>
        Email: {identity_data['email']}<br>
        Registration No: {identity_data['reg_no']}<br>
        <br>
        <b>Security:</b><br>
        Mode: {security_mode}
        """
        self.summary_text.setText(summary)


# ──────────────────────────────────────────────────────────────────────────────
# First-Run Wizard
# ──────────────────────────────────────────────────────────────────────────────


class FirstRunWizard(QWizard):
    """Multi-step wizard for SwiftLedger initial setup."""

    def __init__(self, parent=None, db_path: str = "swiftledger.db"):
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowTitle("SwiftLedger - First Run Setup")
        self.setWindowIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DesktopIcon))
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        # Create pages
        self.welcome_page = WelcomePage()
        self.identity_page = IdentityPage()
        self.security_page = SecurityPage()
        self.finalize_page = FinalizePage()

        # Add pages in order
        self.addPage(self.welcome_page)
        self.addPage(self.identity_page)
        self.addPage(self.security_page)
        self.addPage(self.finalize_page)

        # Connect finish signal
        self.finished.connect(self._on_wizard_finished)

    def _on_wizard_finished(self) -> None:
        """Handle wizard completion: save settings, log event, and launch dashboard."""
        if self.result() != QWizard.Accepted.value:
            return

        try:
            # Initialize database
            db_conn = init_db(self.db_path)
            db_conn.close()

            # Collect form data
            identity_data = self.identity_page.get_data()
            security_mode = self.security_page.get_security_mode()
            credential = self.security_page.get_credential()

            # Prepare settings dictionary
            settings_data = {
                "society_name": identity_data["society_name"],
                "street": identity_data["street"],
                "city_state": identity_data["city_state"],
                "phone": identity_data["phone"],
                "email": identity_data["email"],
                "reg_no": identity_data["reg_no"],
                "security_mode": security_mode,
            }

            # Hash credential if provided
            if credential:
                settings_data["auth_hash"] = hash_credential(credential)

            # Save settings to database
            save_settings(settings_data, self.db_path)

            # Log the initialization event
            log_event(
                user="Admin",
                category="Security",
                description="Initial system setup completed",
                status="Success",
                db_path=self.db_path
            )

            # Show success message
            QMessageBox.information(
                self,
                "Setup Complete",
                "SwiftLedger has been initialized successfully!\n"
                "You can now launch the main application."
            )

            # Emit signal to parent to launch dashboard
            parent = self.parent()
            if parent is not None and hasattr(parent, 'launch_dashboard'):
                cast(object, parent).launch_dashboard()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Initialization Error",
                f"An error occurred during setup:\n{str(e)}"
            )


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    wizard = FirstRunWizard()
    wizard.show()
    sys.exit(app.exec())
