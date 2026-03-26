"""
First-run wizard for SwiftLedger initial setup.

Guides users through welcome, identity setup, security configuration,
and system finalization steps.
"""

import sys
import re
from pathlib import Path
from typing import cast, Any

from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QMessageBox, QDialog, QStyle
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_init import init_db, save_settings, log_event
from security import hash_credential, generate_secure_token
from ui.reports_page import generate_and_open_user_guide
from ui.widgets import UppercaseLineEdit


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
        footer = QLabel("Designed and Developed by Zabdiel  |  www.zabdiel.tech")
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
        self.society_input = UppercaseLineEdit()
        self.society_input.setPlaceholderText("e.g., Main Street Savings Society")
        layout.addWidget(society_label)
        layout.addWidget(self.society_input)

        # Address
        street_label = QLabel("Address:")
        self.street_input = UppercaseLineEdit()
        self.street_input.setPlaceholderText("e.g., 123 Main Street")
        layout.addWidget(street_label)
        layout.addWidget(self.street_input)

        # City/State
        city_label = QLabel("State/Country:")
        self.city_input = UppercaseLineEdit()
        self.city_input.setPlaceholderText("e.g., Abuja,Nigeria")
        layout.addWidget(city_label)
        layout.addWidget(self.city_input)

        # Phone
        phone_label = QLabel("Phone:")
        self.phone_input = UppercaseLineEdit()
        self.phone_input.setPlaceholderText("e.g., +234 7025 067 494")
        layout.addWidget(phone_label)
        layout.addWidget(self.phone_input)

        # Email
        email_label = QLabel("Email:")
        self.email_input = UppercaseLineEdit(force_uppercase=False)
        self.email_input.setPlaceholderText("e.g., contact@society.com")
        layout.addWidget(email_label)
        layout.addWidget(self.email_input)

        layout.addStretch()

    def get_data(self) -> dict:
        """Return form data as a dictionary."""
        return {
            "society_name": self.society_input.text(),
            "street": self.street_input.text(),
            "city_state": self.city_input.text(),
            "phone": self.phone_input.text(),
            "email": self.email_input.text(),
        }

    def validatePage(self) -> bool:
        """Validate that required fields are filled."""
        data = self.get_data()
        required_fields = ["society_name", "street", "city_state", "phone", "email"]
        
        for field in required_fields:
            if not data[field].strip():
                QMessageBox.warning(
                    self,
                    "Missing Information",
                    f"Please enter a valid {field.replace('_', ' ').title()}."
                )
                return False

        email = data["email"].strip()
        email_pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
        if re.match(email_pattern, email) is None:
            QMessageBox.warning(
                self,
                "Invalid Email",
                "Please enter a valid email address (e.g., name@example.com)."
            )
            return False

        phone_digits = "".join(ch for ch in data["phone"] if ch.isdigit())
        if len(phone_digits) < 10:
            QMessageBox.warning(
                self,
                "Invalid Phone",
                "Phone number should contain at least 10 digits."
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
        ])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        layout.addWidget(self.mode_combo)

        layout.addSpacing(20)

        # Credential input
        self.credential_label = QLabel("Enter your PIN/Password:")
        self.credential_label.setFont(mode_font)
        layout.addWidget(self.credential_label)

        self.credential_input = QLineEdit()
        self.credential_input.setEchoMode(QLineEdit.EchoMode.Password)
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
            "For PIN/Password, you'll need to set a secure code above."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        layout.addWidget(info_label)

        layout.addStretch()

        # Initial state
        self._on_mode_changed()

    def _on_mode_changed(self) -> None:
        """Update placeholders based on selected mode."""
        if "PIN" in self.mode_combo.currentText():
            self.credential_input.setPlaceholderText("Enter 4-6 digit PIN")
            self.confirm_input.setPlaceholderText("Re-enter PIN")
        else:
            self.credential_input.setPlaceholderText("Enter password")
            self.confirm_input.setPlaceholderText("Re-enter password")

    def get_security_mode(self) -> str:
        """Return the selected security mode."""
        mode_text = self.mode_combo.currentText()
        if "PIN" in mode_text:
            return "pin"
        return "password"

    def get_credential(self) -> str:
        """Return the entered credential."""
        return self.credential_input.text()

    def validatePage(self) -> bool:
        """Validate security configuration."""
        mode = self.get_security_mode()

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

        if mode == "pin":
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
        self.summary_text.setStyleSheet(
            "background-color: #ecf0f1; color: #2c3e50; padding: 10px; border-radius: 5px;"
        )
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
        raw_security_mode = wizard.security_page.get_security_mode()
        security_mode = "PIN" if raw_security_mode == "pin" else "Password"

        summary = f"""
        <b>Organization Information:</b><br>
        Society Name: {identity_data['society_name']}<br>
        Address: {identity_data['street']}<br>
        City/State: {identity_data['city_state']}<br>
        Phone: {identity_data['phone']}<br>
        Email: {identity_data['email']}<br>
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
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))
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
        if self.result() != QDialog.DialogCode.Accepted:
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
            recovery_key_plain = generate_secure_token(6).upper()
            settings_data = {
                "society_name": identity_data["society_name"],
                "street": identity_data["street"],
                "address": identity_data["street"],
                "city_state": identity_data["city_state"],
                "phone": identity_data["phone"],
                "email": identity_data["email"],
                "security_mode": security_mode,
                "recovery_key_hash": hash_credential(recovery_key_plain),
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

            # Generate and auto-open the Quick Start Manual
            try:
                generate_and_open_user_guide(settings_data)
            except Exception:
                pass  # Non-critical; don't block setup completion

            # Show success message
            QMessageBox.information(
                self,
                "Setup Complete",
                "SwiftLedger has been initialized successfully!\n"
                "Your Quick Start Manual has been opened.\n"
                "You can now launch the main application.\n\n"
                f"Recovery Key (save this securely):\n{recovery_key_plain}"
            )

            # Emit signal to parent to launch dashboard
            parent = self.parent()
            if parent is not None and hasattr(parent, 'launch_dashboard'):
                cast(Any, parent).launch_dashboard()

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
