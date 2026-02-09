"""
Settings / Preferences page for SwiftLedger.
Lets the user toggle charts, set auto-lock timeout, and save to system_settings.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QCheckBox, QSlider, QMessageBox,
    QSpinBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db_init import save_settings, log_event
from database.queries import get_system_settings


class SettingsPage(QWidget):
    """Preferences panel — charts toggle, auto-lock timeout, and Apply button."""

    def __init__(self, db_path: str = "swiftledger.db"):
        super().__init__()
        self.db_path = db_path
        self._build_ui()
        self._load_current_settings()

    # ── UI ───────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(20)

        # Title
        title = QLabel("Settings")
        tf = QFont("Arial", 18)
        tf.setBold(True)
        title.setFont(tf)
        main.addWidget(title)

        # ── Preferences group ───────────────────────────────────────
        pref_group = QGroupBox("Preferences")
        pref_group.setFont(QFont("Arial", 12))
        form = QFormLayout(pref_group)
        form.setContentsMargins(14, 20, 14, 14)
        form.setSpacing(16)

        # Show charts toggle
        self.chk_charts = QCheckBox("Show Financial Charts on Dashboard")
        self.chk_charts.setFont(QFont("Arial", 11))
        form.addRow(self.chk_charts)

        # Auto-lock timeout
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

        form.addRow("Auto-Lock Timeout:", timeout_row)

        main.addWidget(pref_group)

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

    # ── Sync helpers ─────────────────────────────────────────────────

    def _sync_timeout_display(self, value: int) -> None:
        self.spin_timeout.blockSignals(True)
        self.spin_timeout.setValue(value)
        self.spin_timeout.blockSignals(False)

    def _sync_timeout_slider(self, value: int) -> None:
        self.slider_timeout.blockSignals(True)
        self.slider_timeout.setValue(value)
        self.slider_timeout.blockSignals(False)

    # ── Load / Save ──────────────────────────────────────────────────

    def _load_current_settings(self) -> None:
        ok, settings = get_system_settings(self.db_path)
        if not ok or not settings:
            return

        self.chk_charts.setChecked(bool(settings.get('show_charts', 0)))

        timeout = int(settings.get('timeout_minutes', 10))
        self.slider_timeout.setValue(timeout)
        self.spin_timeout.setValue(timeout)

    def _apply_settings(self) -> None:
        data = {
            'show_charts': 1 if self.chk_charts.isChecked() else 0,
            'timeout_minutes': self.spin_timeout.value(),
        }

        try:
            save_settings(data, self.db_path)
            log_event(
                user="Admin",
                category="Settings",
                description=(
                    f"Preferences updated (charts={data['show_charts']}, "
                    f"timeout_minutes={data['timeout_minutes']})"
                ),
                status="Success",
                db_path=self.db_path,
            )
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
