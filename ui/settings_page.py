"""
Settings / Preferences page for SwiftLedger.
Lets the user toggle charts, alerts, theme, text scale, auto-lock timeout.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QCheckBox, QSlider, QMessageBox,
    QSpinBox, QComboBox, QScrollArea, QFrame, QLineEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db_init import save_settings, log_event
from database.queries import get_system_settings
from security import hash_credential


class SettingsPage(QWidget):
    """Preferences panel — theme, text scale, charts, alerts, timeout."""

    # Emitted after the user clicks Apply so MainWindow can re-theme live
    settings_changed = Signal()

    def __init__(self, db_path: str = "swiftledger.db"):
        super().__init__()
        self.db_path = db_path
        self.current_auth_hash = ""
        self._build_ui()
        self._load_current_settings()

    # ── UI ───────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(20)

        # Title
        title = QLabel("Settings")
        tf = QFont("Arial", 18)
        tf.setBold(True)
        title.setFont(tf)
        main.addWidget(title)

        # ── Appearance group ────────────────────────────────────────
        appear_group = QGroupBox("Appearance")
        appear_group.setFont(QFont("Arial", 12))
        appear_form = QFormLayout(appear_group)
        appear_form.setContentsMargins(14, 20, 14, 14)
        appear_form.setSpacing(16)

        # Theme
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Dark", "Light"])
        self.combo_theme.setFont(QFont("Arial", 11))
        appear_form.addRow("Theme:", self.combo_theme)

        # Text scale
        scale_row = QHBoxLayout()
        self.slider_scale = QSlider(Qt.Orientation.Horizontal)
        self.slider_scale.setRange(80, 150)
        self.slider_scale.setValue(100)
        self.slider_scale.setTickInterval(10)
        self.slider_scale.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_scale.valueChanged.connect(self._sync_scale_display)

        self.lbl_scale = QLabel("100 %")
        self.lbl_scale.setMinimumWidth(50)
        scale_row.addWidget(self.slider_scale)
        scale_row.addWidget(self.lbl_scale)
        appear_form.addRow("Text Scale:", scale_row)

        main.addWidget(appear_group)

        # ── Feature Toggles group ───────────────────────────────────
        toggle_group = QGroupBox("Feature Toggles")
        toggle_group.setFont(QFont("Arial", 12))
        toggle_form = QFormLayout(toggle_group)
        toggle_form.setContentsMargins(14, 20, 14, 14)
        toggle_form.setSpacing(16)

        self.chk_charts = QCheckBox("Show Financial Charts on Dashboard")
        self.chk_charts.setFont(QFont("Arial", 11))
        toggle_form.addRow(self.chk_charts)

        self.chk_alerts = QCheckBox("Show Automated Loan Alerts on Dashboard")
        self.chk_alerts.setFont(QFont("Arial", 11))
        toggle_form.addRow(self.chk_alerts)

        main.addWidget(toggle_group)

        # ── Security group ──────────────────────────────────────────
        sec_group = QGroupBox("Security")
        sec_group.setFont(QFont("Arial", 12))
        sec_form = QFormLayout(sec_group)
        sec_form.setContentsMargins(14, 20, 14, 14)
        sec_form.setSpacing(16)

        # Security mode
        self.combo_security_mode = QComboBox()
        self.combo_security_mode.addItems(["PIN", "Password", "System Auth"])
        self.combo_security_mode.setFont(QFont("Arial", 11))
        self.combo_security_mode.currentTextChanged.connect(self._sync_security_placeholders)
        sec_form.addRow("Security Mode:", self.combo_security_mode)

        # New credential fields
        self.input_new_credential = QLineEdit()
        self.input_new_credential.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_new_credential.setMinimumHeight(34)
        sec_form.addRow("New Credential:", self.input_new_credential)

        self.input_confirm_credential = QLineEdit()
        self.input_confirm_credential.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_confirm_credential.setMinimumHeight(34)
        sec_form.addRow("Confirm Credential:", self.input_confirm_credential)

        timeout_row = QHBoxLayout()
        self.slider_timeout = QSlider(Qt.Orientation.Horizontal)
        self.slider_timeout.setRange(1, 60)
        self.slider_timeout.setValue(10)
        self.slider_timeout.setTickInterval(5)
        self.slider_timeout.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_timeout.valueChanged.connect(self._sync_timeout_display)

        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(1, 60)
        self.spin_timeout.setValue(10)
        self.spin_timeout.setSuffix(" min")
        self.spin_timeout.valueChanged.connect(self._sync_timeout_slider)

        timeout_row.addWidget(self.slider_timeout)
        timeout_row.addWidget(self.spin_timeout)

        sec_form.addRow("Auto-Lock Timeout:", timeout_row)
        main.addWidget(sec_group)

        # ── Apply button ────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_apply = QPushButton("Apply")
        self.btn_apply.setMinimumHeight(40)
        self.btn_apply.setMinimumWidth(140)
        bf = QFont("Arial", 11)
        bf.setBold(True)
        self.btn_apply.setFont(bf)
        self.btn_apply.setStyleSheet(
            "QPushButton { background-color: #2980b9; color: white; "
            "border-radius: 6px; padding: 8px 20px; } "
            "QPushButton:hover { background-color: #3498db; }"
        )
        self.btn_apply.clicked.connect(self._apply_settings)
        btn_row.addWidget(self.btn_apply)

        main.addLayout(btn_row)
        main.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ── Sync helpers ─────────────────────────────────────────────────

    def _sync_scale_display(self, value: int) -> None:
        self.lbl_scale.setText(f"{value} %")

    def _sync_timeout_display(self, value: int) -> None:
        self.spin_timeout.blockSignals(True)
        self.spin_timeout.setValue(value)
        self.spin_timeout.blockSignals(False)

    def _sync_timeout_slider(self, value: int) -> None:
        self.slider_timeout.blockSignals(True)
        self.slider_timeout.setValue(value)
        self.slider_timeout.blockSignals(False)

    def _sync_security_placeholders(self) -> None:
        mode = self.combo_security_mode.currentText().lower().replace(" ", "_")
        if mode == "pin":
            self.input_new_credential.setPlaceholderText("4-6 digit PIN")
            self.input_confirm_credential.setPlaceholderText("Re-enter PIN")
            self.input_new_credential.setEnabled(True)
            self.input_confirm_credential.setEnabled(True)
        elif mode == "password":
            self.input_new_credential.setPlaceholderText("New password (min 6 chars)")
            self.input_confirm_credential.setPlaceholderText("Re-enter password")
            self.input_new_credential.setEnabled(True)
            self.input_confirm_credential.setEnabled(True)
        else:
            self.input_new_credential.setPlaceholderText("Not required for System Auth")
            self.input_confirm_credential.setPlaceholderText("Not required for System Auth")
            self.input_new_credential.setEnabled(False)
            self.input_confirm_credential.setEnabled(False)

    # ── Load / Save ──────────────────────────────────────────────────

    def _load_current_settings(self) -> None:
        ok, settings = get_system_settings(self.db_path)
        if not ok or not settings:
            return

        self.chk_charts.setChecked(bool(settings.get('show_charts', 0)))
        self.chk_alerts.setChecked(bool(settings.get('show_alerts', 1)))

        theme = str(settings.get('theme', 'dark')).capitalize()
        idx = self.combo_theme.findText(theme)
        if idx >= 0:
            self.combo_theme.setCurrentIndex(idx)

        scale_pct = int(float(settings.get('text_scale', 1.0)) * 100)
        self.slider_scale.setValue(max(80, min(150, scale_pct)))
        self.lbl_scale.setText(f"{self.slider_scale.value()} %")

        timeout = int(settings.get('timeout_minutes', 10))
        self.slider_timeout.setValue(timeout)
        self.spin_timeout.setValue(timeout)

        self.current_auth_hash = str(settings.get("auth_hash") or "")
        mode = str(settings.get("security_mode") or "pin").lower().replace(" ", "_")
        mode_label = "System Auth" if mode == "system_auth" else mode.capitalize()
        idx = self.combo_security_mode.findText(mode_label)
        if idx >= 0:
            self.combo_security_mode.setCurrentIndex(idx)
        self._sync_security_placeholders()

    def _apply_settings(self) -> None:
        mode = self.combo_security_mode.currentText().lower().replace(" ", "_")
        new_cred = self.input_new_credential.text().strip()
        confirm = self.input_confirm_credential.text().strip()

        # Validate credential change if provided or required
        if mode in ("pin", "password"):
            if not self.current_auth_hash and not new_cred:
                QMessageBox.warning(
                    self, "Credential Required",
                    "Please set a credential for the selected security mode."
                )
                return
            if new_cred or confirm:
                if new_cred != confirm:
                    QMessageBox.warning(self, "Mismatch", "Credential confirmation does not match.")
                    return
                if mode == "pin":
                    if not new_cred.isdigit() or not (4 <= len(new_cred) <= 6):
                        QMessageBox.warning(self, "Invalid PIN", "PIN must be 4-6 digits.")
                        return
                if mode == "password":
                    if len(new_cred) < 6:
                        QMessageBox.warning(self, "Weak Password", "Password must be at least 6 characters.")
                        return

        data = {
            'show_charts': 1 if self.chk_charts.isChecked() else 0,
            'show_alerts': 1 if self.chk_alerts.isChecked() else 0,
            'theme': self.combo_theme.currentText().lower(),
            'text_scale': round(self.slider_scale.value() / 100.0, 2),
            'timeout_minutes': self.spin_timeout.value(),
            'security_mode': mode,
        }

        if new_cred and mode in ("pin", "password"):
            data['auth_hash'] = hash_credential(new_cred)

        try:
            save_settings(data, self.db_path)
            log_event(
                user="Admin",
                category="Settings",
                description=(
                    f"Preferences updated (theme={data['theme']}, "
                    f"scale={data['text_scale']}, charts={data['show_charts']}, "
                    f"alerts={data['show_alerts']}, timeout={data['timeout_minutes']}, "
                    f"security_mode={data['security_mode']})"
                ),
                status="Success",
                db_path=self.db_path,
            )
            self.settings_changed.emit()
            QMessageBox.information(self, "Saved", "Settings applied successfully.")
        except Exception as e:
            log_event(
                user="Admin",
                category="Settings",
                description=f"Settings update failed (error: {e})",
                status="Failed",
                db_path=self.db_path,
            )
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{e}")
