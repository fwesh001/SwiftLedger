"""
Login / Authentication screen for SwiftLedger.

Reads the configured security_mode from system_settings and presents
the appropriate authentication gate (PIN, Password, or System Auth).
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

sys.path.insert(0, str(Path(__file__).parent.parent))
from database.queries import get_system_settings
from database.db_init import log_event
from security import verify_credential, check_system_auth


class LoginScreen(QWidget):
    """
    Full-screen login gate.

    Emits ``login_successful`` when the user authenticates correctly.
    The host (main.py) connects that signal to swap in the MainWindow.
    """

    login_successful = Signal()

    def __init__(self, db_path: str = "swiftledger.db"):
        super().__init__()
        self.db_path = db_path
        self.security_mode = "pin"
        self.auth_hash = ""
        self._load_security_settings()
        self._build_ui()

    # ── Load settings ────────────────────────────────────────────────

    def _load_security_settings(self) -> None:
        """Read security_mode and auth_hash from the database."""
        ok, settings = get_system_settings(self.db_path)
        if ok and settings:
            mode = settings.get("security_mode") or "pin"
            self.security_mode = str(mode).strip().lower()
            self.auth_hash = str(settings.get("auth_hash") or "")

    # ── UI ───────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setWindowTitle("SwiftLedger — Login")
        self.setMinimumSize(420, 340)

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setFixedSize(380, 300)
        card.setStyleSheet(
            "QFrame { background: #2b2b2b; border: 1px solid #444; "
            "border-radius: 12px; }"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 24, 30, 24)
        card_layout.setSpacing(14)

        # Logo / branding
        logo = QLabel("SwiftLedger")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(
            "font-size: 26px; font-weight: bold; color: #3498db; border: none;"
        )
        card_layout.addWidget(logo)

        tagline = QLabel("Transparent. Simple. Secure.")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setStyleSheet(
            "font-size: 11px; color: #7f8c8d; font-style: italic; border: none;"
        )
        card_layout.addWidget(tagline)

        card_layout.addSpacing(8)

        # Credential input (hidden for system_auth mode)
        self.input_credential = QLineEdit()
        self.input_credential.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_credential.setMinimumHeight(38)
        self.input_credential.setStyleSheet(
            "QLineEdit { background: #333; color: #fff; border: 1px solid #555; "
            "border-radius: 6px; padding: 6px 12px; font-size: 14px; }"
        )

        if self.security_mode == "pin":
            self.input_credential.setPlaceholderText("Enter your PIN")
        elif self.security_mode == "password":
            self.input_credential.setPlaceholderText("Enter your password")
        else:
            # system_auth — hide the text field, show a different prompt
            self.input_credential.setVisible(False)

        card_layout.addWidget(self.input_credential)

        # Login button
        self.btn_login = QPushButton(
            "Authenticate with Windows"
            if self.security_mode == "system_auth"
            else "Unlock"
        )
        self.btn_login.setMinimumHeight(40)
        bf = QFont("Arial", 11)
        bf.setBold(True)
        self.btn_login.setFont(bf)
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setStyleSheet(
            "QPushButton { background-color: #2980b9; color: white; "
            "border-radius: 6px; padding: 8px 20px; } "
            "QPushButton:hover { background-color: #3498db; }"
        )
        self.btn_login.clicked.connect(self._attempt_login)
        card_layout.addWidget(self.btn_login)

        # Enter key triggers login
        self.input_credential.returnPressed.connect(self._attempt_login)

        card_layout.addStretch()
        outer.addWidget(card)

    # ── Authentication logic ─────────────────────────────────────────

    def _attempt_login(self) -> None:
        if self.security_mode == "system_auth":
            self._do_system_auth()
        else:
            self._do_credential_auth()

    def _do_credential_auth(self) -> None:
        """Verify PIN or password against stored hash."""
        user_input = self.input_credential.text().strip()
        if not user_input:
            QMessageBox.warning(self, "Input Required", "Please enter your credential.")
            return

        if not self.auth_hash:
            # No hash stored — allow entry and log a warning
            log_event(
                user="Admin",
                category="Security",
                description="Login allowed (no auth_hash configured — run setup wizard)",
                status="Success",
                db_path=self.db_path,
            )
            self.login_successful.emit()
            return

        if verify_credential(user_input, self.auth_hash):
            log_event(
                user="Admin",
                category="Security",
                description="Successful login",
                status="Success",
                db_path=self.db_path,
            )
            self.login_successful.emit()
        else:
            log_event(
                user="Admin",
                category="Security",
                description="Failed login attempt",
                status="Failed",
                db_path=self.db_path,
            )
            QMessageBox.critical(
                self, "Authentication Failed",
                "Incorrect credential. Please try again.",
            )
            self.input_credential.clear()

    def _do_system_auth(self) -> None:
        """Use Windows credential provider for authentication."""
        result = check_system_auth()
        if result:
            log_event(
                user="Admin",
                category="Security",
                description="Successful system authentication",
                status="Success",
                db_path=self.db_path,
            )
            self.login_successful.emit()
        else:
            log_event(
                user="Admin",
                category="Security",
                description="Failed system authentication attempt",
                status="Failed",
                db_path=self.db_path,
            )
            QMessageBox.critical(
                self, "Authentication Failed",
                "Windows authentication was cancelled or failed.\n"
                "Please try again.",
            )
