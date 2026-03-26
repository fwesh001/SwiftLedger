"""
Login / Authentication screen for SwiftLedger.

Reads the configured security_mode from system_settings and presents
the appropriate authentication gate (PIN or Password).
"""

import sys
import re
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox, QFrame, QInputDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

sys.path.insert(0, str(Path(__file__).parent.parent))
from database.queries import get_system_settings, reset_credential_with_recovery_key
from database.db_init import log_event
from security import verify_credential


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
        self.recovery_key_hash = ""
        self._load_security_settings()
        self._build_ui()

    # ── Load settings ────────────────────────────────────────────────

    def _load_security_settings(self) -> None:
        """Read security_mode and auth_hash from the database."""
        ok, settings = get_system_settings(self.db_path)
        if ok and settings:
            mode = str(settings.get("security_mode") or "password")
            normalized = mode.strip().lower().replace(" ", "_")
            if normalized in ("system", "system_auth", "system_authentication"):
                normalized = "password"
            if normalized not in ("pin", "password"):
                normalized = "password"
            self.security_mode = normalized
            self.auth_hash = str(settings.get("auth_hash") or "")
            self.recovery_key_hash = str(settings.get("recovery_key_hash") or "")

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

        # Credential input
        self.input_credential = QLineEdit()
        self.input_credential.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_credential.setMinimumHeight(38)
        self.input_credential.setStyleSheet(
            "QLineEdit { background: #333; color: #fff; border: 1px solid #555; "
            "border-radius: 6px; padding: 6px 12px; font-size: 14px; }"
        )

        if self.security_mode == "pin":
            self.input_credential.setPlaceholderText("Enter your PIN")
        else:
            self.input_credential.setPlaceholderText("Enter your password")

        card_layout.addWidget(self.input_credential)

        # Login button
        self.btn_login = QPushButton("Unlock")
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

        self.btn_forgot = QPushButton("Forgot Password?")
        self.btn_forgot.setMinimumHeight(30)
        self.btn_forgot.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_forgot.setStyleSheet(
            "QPushButton { background: transparent; color: #7fb3d5; border: none; text-decoration: underline; } "
            "QPushButton:hover { color: #aed6f1; }"
        )
        self.btn_forgot.clicked.connect(self._forgot_password_flow)
        card_layout.addWidget(self.btn_forgot, alignment=Qt.AlignmentFlag.AlignCenter)

        # Enter key triggers login
        self.input_credential.returnPressed.connect(self._attempt_login)

        card_layout.addStretch()
        outer.addWidget(card)

    # ── Authentication logic ─────────────────────────────────────────

    def _attempt_login(self) -> None:
        self._do_credential_auth()

    def _do_credential_auth(self) -> None:
        """Verify PIN or password against stored hash."""
        user_input = self.input_credential.text().strip()
        if not user_input:
            QMessageBox.warning(self, "Input Required", "Please enter your credential.")
            return

        if not self.auth_hash:
            # Fail closed: never allow login when auth hash is missing.
            log_event(
                user="Admin",
                category="Security",
                description="Login blocked (auth_hash not configured)",
                status="Failed",
                db_path=self.db_path,
            )
            QMessageBox.critical(
                self,
                "Security Configuration Required",
                "Credential is not configured for this installation.\n"
                "Use Forgot Password with a valid Recovery Key or re-run setup.",
            )
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

    def _forgot_password_flow(self) -> None:
        """Reset credential using recovery key."""
        ok, settings = get_system_settings(self.db_path)
        if not ok or not settings:
            QMessageBox.critical(self, "Recovery Unavailable", "Could not load security settings.")
            return

        self.recovery_key_hash = str(settings.get("recovery_key_hash") or "")
        self.security_mode = str(settings.get("security_mode") or self.security_mode).strip().lower().replace(" ", "_")
        if self.security_mode not in ("pin", "password"):
            self.security_mode = "password"

        if not self.recovery_key_hash:
            QMessageBox.warning(
                self,
                "Recovery Not Configured",
                "Recovery key is not configured for this installation.\n"
                "Open Settings after login to generate one.",
            )
            return

        recovery_key, ok = QInputDialog.getText(
            self,
            "Forgot Password",
            "Enter your recovery key:",
            QLineEdit.EchoMode.Normal,
        )
        if not ok:
            return

        normalized_key = (recovery_key or "").strip().upper()
        if re.fullmatch(r"[A-F0-9]{12}", normalized_key) is None:
            QMessageBox.critical(self, "Invalid Recovery Key", "Recovery key format is invalid.")
            return

        if not verify_credential(normalized_key, self.recovery_key_hash):
            log_event(
                user="Admin",
                category="Security",
                description="Credential reset failed (invalid recovery key)",
                status="Failed",
                db_path=self.db_path,
            )
            QMessageBox.critical(self, "Invalid Recovery Key", "The recovery key you entered is incorrect.")
            return

        new_credential, ok = QInputDialog.getText(
            self,
            "New Credential",
            "Enter new credential for current mode:\n"
            f"{('PIN (4-6 digits)' if self.security_mode == 'pin' else 'Password (min 6 chars)')}",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return

        confirm, ok = QInputDialog.getText(
            self,
            "Confirm Credential",
            "Re-enter new credential:",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return

        if (new_credential or "") != (confirm or ""):
            QMessageBox.warning(self, "Mismatch", "Credential confirmation does not match.")
            return

        mode = self.security_mode if self.security_mode in ("pin", "password") else "password"
        ok_reset, message = reset_credential_with_recovery_key(
            self.db_path,
            normalized_key,
            new_credential,
            mode,
        )
        if not ok_reset:
            QMessageBox.critical(self, "Reset Failed", message)
            return

        self._load_security_settings()
        self.input_credential.clear()
        QMessageBox.information(
            self,
            "Reset Successful",
            "Credential has been reset. You can now log in with the new credential.",
        )

