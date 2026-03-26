"""
Settings / Preferences page for SwiftLedger.
Lets the user toggle charts, alerts, theme, text scale, auto-lock timeout.
"""

import sys
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QCheckBox, QSlider, QMessageBox,
    QSpinBox, QComboBox, QScrollArea, QFrame, QLineEdit, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QDialog,
    QDialogButtonBox,
    QTabWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHeaderView

sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db_init import save_settings, log_event
from ui.widgets import UppercaseLineEdit
from database.queries import (
    get_system_settings,
    get_loan_products,
    add_loan_product,
    update_loan_product,
    set_loan_product_active,
)
from security import hash_credential, generate_secure_token


class SettingsPage(QWidget):
    """Preferences panel — theme, text scale, charts, alerts, timeout."""

    # Emitted after the user clicks Apply so MainWindow can re-theme live
    settings_changed = Signal()

    def _apply_form_rhythm(self, layout: QFormLayout) -> None:
        """Apply consistent spacing/alignment rhythm for form rows."""
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(10)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

    def __init__(self, db_path: str = "swiftledger.db"):
        super().__init__()
        self.db_path = db_path
        self.current_auth_hash = ""
        self.pending_recovery_key = ""
        self._build_ui()
        self._load_current_settings()
        self._load_loan_products_table()

    # ── UI ───────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(14)

        # Title
        title = QLabel("Settings")
        tf = QFont("Arial", 18)
        tf.setBold(True)
        title.setFont(tf)
        outer.addWidget(title)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setTabPosition(QTabWidget.TabPosition.North)
        tabs.setMovable(False)
        outer.addWidget(tabs)

        def make_tab_container() -> tuple[QWidget, QVBoxLayout]:
            tab_scroll = QScrollArea()
            tab_scroll.setWidgetResizable(True)
            tab_scroll.setFrameShape(QFrame.Shape.NoFrame)
            tab_content = QWidget()
            tab_layout = QVBoxLayout(tab_content)
            tab_layout.setContentsMargins(8, 8, 8, 8)
            tab_layout.setSpacing(16)
            tab_scroll.setWidget(tab_content)
            return tab_scroll, tab_layout

        general_tab, general_layout = make_tab_container()
        policy_tab, policy_layout = make_tab_container()
        security_tab, security_layout = make_tab_container()

        tabs.addTab(general_tab, "General")
        tabs.addTab(policy_tab, "Organization & Loans")
        tabs.addTab(security_tab, "Security")

        # ── Appearance group ────────────────────────────────────────
        appear_group = QGroupBox("Appearance")
        appear_group.setFont(QFont("Arial", 12))
        appear_form = QFormLayout(appear_group)
        self._apply_form_rhythm(appear_form)

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

        general_layout.addWidget(appear_group)

        # ── Feature Toggles group ───────────────────────────────────
        toggle_group = QGroupBox("Feature Toggles")
        toggle_group.setFont(QFont("Arial", 12))
        toggle_form = QFormLayout(toggle_group)
        self._apply_form_rhythm(toggle_form)

        self.chk_charts = QCheckBox("Show Financial Charts on Dashboard")
        self.chk_charts.setFont(QFont("Arial", 11))
        toggle_form.addRow(self.chk_charts)

        self.chk_alerts = QCheckBox("Show Automated Loan Alerts on Dashboard")
        self.chk_alerts.setFont(QFont("Arial", 11))
        toggle_form.addRow(self.chk_alerts)

        general_layout.addWidget(toggle_group)

        # ── Organization & Loan Policy ─────────────────────────────
        policy_group = QGroupBox("Organization & Loan Policy")
        policy_group.setFont(QFont("Arial", 12))
        policy_form = QFormLayout(policy_group)
        self._apply_form_rhythm(policy_form)

        self.input_society_name = UppercaseLineEdit()
        self.input_society_name.setMinimumHeight(32)
        policy_form.addRow("Society Name:", self.input_society_name)

        self.input_address = UppercaseLineEdit()
        self.input_address.setMinimumHeight(32)
        policy_form.addRow("Address:", self.input_address)

        self.input_city_state = UppercaseLineEdit()
        self.input_city_state.setMinimumHeight(32)
        policy_form.addRow("City/State:", self.input_city_state)

        self.input_phone = UppercaseLineEdit()
        self.input_phone.setMinimumHeight(32)
        policy_form.addRow("Phone:", self.input_phone)

        self.input_email = UppercaseLineEdit(force_uppercase=False)
        self.input_email.setMinimumHeight(32)
        policy_form.addRow("Email:", self.input_email)

        self.input_loan_multiplier = QDoubleSpinBox()
        self.input_loan_multiplier.setRange(0.1, 10.0)
        self.input_loan_multiplier.setSingleStep(0.1)
        self.input_loan_multiplier.setDecimals(2)
        policy_form.addRow("Loan Multiplier:", self.input_loan_multiplier)

        self.input_min_monthly_saving = QDoubleSpinBox()
        self.input_min_monthly_saving.setRange(0.0, 10_000_000.0)
        self.input_min_monthly_saving.setSingleStep(100.0)
        self.input_min_monthly_saving.setPrefix("₦")
        self.input_min_monthly_saving.setDecimals(2)
        policy_form.addRow("Min Savings (eligibility):", self.input_min_monthly_saving)

        self.input_default_interest = QDoubleSpinBox()
        self.input_default_interest.setRange(0.0, 100.0)
        self.input_default_interest.setSingleStep(0.25)
        self.input_default_interest.setSuffix("%")
        self.input_default_interest.setDecimals(2)
        policy_form.addRow("Default Interest Rate:", self.input_default_interest)

        self.input_default_duration = QSpinBox()
        self.input_default_duration.setRange(1, 120)
        self.input_default_duration.setSuffix(" months")
        policy_form.addRow("Default Loan Duration:", self.input_default_duration)

        policy_layout.addWidget(policy_group, 1)

        # ── Loan Products Admin ───────────────────────────────────
        products_group = QGroupBox("Loan Products")
        products_group.setFont(QFont("Arial", 12))
        products_layout = QVBoxLayout(products_group)
        products_layout.setContentsMargins(14, 20, 14, 14)
        products_layout.setSpacing(10)

        self.table_loan_products = QTableWidget()
        self.table_loan_products.setColumnCount(6)
        self.table_loan_products.setHorizontalHeaderLabels(
            ["Name", "Max Amount", "Rate", "Duration", "Status", "ID"]
        )
        self.table_loan_products.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_loan_products.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_loan_products.horizontalHeader().setStretchLastSection(True)
        self.table_loan_products.verticalHeader().setVisible(False)
        self.table_loan_products.setAlternatingRowColors(True)
        products_header = self.table_loan_products.horizontalHeader()
        products_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        products_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        products_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        products_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        products_header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_loan_products.setColumnHidden(5, True)
        self.table_loan_products.setMinimumHeight(360)
        products_layout.addWidget(self.table_loan_products, 1)

        products_btn_row = QHBoxLayout()
        self.btn_product_add = QPushButton("Add")
        self.btn_product_add.setMinimumWidth(90)
        self.btn_product_add.clicked.connect(self._add_loan_product)
        products_btn_row.addWidget(self.btn_product_add)

        self.btn_product_edit = QPushButton("Edit")
        self.btn_product_edit.setMinimumWidth(90)
        self.btn_product_edit.clicked.connect(self._edit_loan_product)
        products_btn_row.addWidget(self.btn_product_edit)

        self.btn_product_toggle = QPushButton("Activate/Deactivate")
        self.btn_product_toggle.setMinimumWidth(170)
        self.btn_product_toggle.clicked.connect(self._toggle_loan_product_status)
        products_btn_row.addWidget(self.btn_product_toggle)

        self.btn_product_refresh = QPushButton("Refresh")
        self.btn_product_refresh.setMinimumWidth(100)
        self.btn_product_refresh.clicked.connect(self._load_loan_products_table)
        products_btn_row.addWidget(self.btn_product_refresh)
        products_btn_row.addStretch()
        products_layout.addLayout(products_btn_row)

        policy_layout.addWidget(products_group, 2)

        # ── Security group ──────────────────────────────────────────
        sec_group = QGroupBox("Security")
        sec_group.setFont(QFont("Arial", 12))
        sec_form = QFormLayout(sec_group)
        self._apply_form_rhythm(sec_form)

        # Security mode
        self.combo_security_mode = QComboBox()
        self.combo_security_mode.addItems(["PIN", "Password"])
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

        self.btn_generate_recovery = QPushButton("Generate New Recovery Key")
        self.btn_generate_recovery.setMinimumHeight(34)
        self.btn_generate_recovery.clicked.connect(self._generate_recovery_key)
        sec_form.addRow("Recovery Key:", self.btn_generate_recovery)

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
        security_layout.addWidget(sec_group)

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

        for layout in (general_layout, policy_layout, security_layout):
            layout.addStretch()

        outer.addLayout(btn_row)

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
        else:
            self.input_new_credential.setPlaceholderText("New password (min 6 chars)")
            self.input_confirm_credential.setPlaceholderText("Re-enter password")
            self.input_new_credential.setEnabled(True)
            self.input_confirm_credential.setEnabled(True)

    def _generate_recovery_key(self) -> None:
        self.pending_recovery_key = generate_secure_token(6).upper()
        QMessageBox.information(
            self,
            "Recovery Key Generated",
            "Save this key in a safe location.\n\n"
            f"Recovery Key:\n{self.pending_recovery_key}\n\n"
            "Click Apply to store it.",
        )

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

        self.input_society_name.setText(str(settings.get('society_name') or ''))
        self.input_address.setText(str(settings.get('address') or settings.get('street') or ''))
        self.input_city_state.setText(str(settings.get('city_state') or ''))
        self.input_phone.setText(str(settings.get('phone') or ''))
        self.input_email.setText(str(settings.get('email') or ''))
        self.input_loan_multiplier.setValue(float(settings.get('loan_multiplier', 2.0) or 2.0))
        self.input_min_monthly_saving.setValue(float(settings.get('min_monthly_saving', 0.0) or 0.0))
        self.input_default_interest.setValue(float(settings.get('default_interest_rate', 12.0) or 12.0))
        self.input_default_duration.setValue(int(settings.get('default_duration', 24) or 24))

        self.current_auth_hash = str(settings.get("auth_hash") or "")
        mode_raw = str(settings.get("security_mode") or "password")
        mode = mode_raw.strip().lower().replace(" ", "_")
        if mode in ("system", "system_auth", "system_authentication"):
            mode = "password"
        if mode not in ("pin", "password"):
            mode = "password"
        mode_label = mode.capitalize()
        idx = self.combo_security_mode.findText(mode_label)
        if idx >= 0:
            self.combo_security_mode.setCurrentIndex(idx)
        self._sync_security_placeholders()

    def _load_loan_products_table(self) -> None:
        ok, products = get_loan_products(self.db_path, active_only=False)
        self.table_loan_products.setRowCount(0)
        if not ok:
            return

        for row_idx, product in enumerate(products):
            self.table_loan_products.insertRow(row_idx)
            product_id = int(product.get("product_id", 0) or 0)
            name = str(product.get("name", ""))
            max_amount = float(product.get("max_amount", 0.0) or 0.0)
            rate = float(product.get("interest_rate", 0.0) or 0.0)
            duration = int(product.get("duration_months", 0) or 0)
            is_active = bool(product.get("is_active", 0))

            self.table_loan_products.setItem(row_idx, 0, QTableWidgetItem(name))
            self.table_loan_products.setItem(row_idx, 1, QTableWidgetItem(f"₦{max_amount:,.2f}"))
            self.table_loan_products.setItem(row_idx, 2, QTableWidgetItem(f"{rate:.2f}%"))
            self.table_loan_products.setItem(row_idx, 3, QTableWidgetItem(f"{duration} months"))
            self.table_loan_products.setItem(row_idx, 4, QTableWidgetItem("Active" if is_active else "Inactive"))
            self.table_loan_products.setItem(row_idx, 5, QTableWidgetItem(str(product_id)))

    def _get_selected_product_id(self) -> int:
        selected = self.table_loan_products.selectionModel().selectedRows()
        if not selected:
            return 0

        row = selected[0].row()
        id_item = self.table_loan_products.item(row, 5)
        if not id_item:
            return 0
        try:
            return int(id_item.text())
        except Exception:
            return 0

    def _open_product_dialog(self, title: str, initial: dict | None = None) -> tuple[bool, dict]:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)

        form = QFormLayout()
        self._apply_form_rhythm(form)
        input_name = UppercaseLineEdit()
        input_name.setPlaceholderText("Product Name")

        input_max = QDoubleSpinBox()
        input_max.setRange(0.0, 100_000_000.0)
        input_max.setPrefix("₦")
        input_max.setDecimals(2)
        input_max.setSingleStep(1000.0)

        input_rate = QDoubleSpinBox()
        input_rate.setRange(0.0, 100.0)
        input_rate.setSuffix("%")
        input_rate.setDecimals(2)
        input_rate.setSingleStep(0.25)

        input_duration = QSpinBox()
        input_duration.setRange(1, 120)
        input_duration.setSuffix(" months")

        if initial:
            input_name.setText(str(initial.get("name", "")))
            input_max.setValue(float(initial.get("max_amount", 0.0) or 0.0))
            input_rate.setValue(float(initial.get("interest_rate", 0.0) or 0.0))
            input_duration.setValue(int(initial.get("duration_months", 1) or 1))

        form.addRow("Name:", input_name)
        form.addRow("Max Amount:", input_max)
        form.addRow("Interest Rate:", input_rate)
        form.addRow("Duration:", input_duration)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False, {}

        return True, {
            "name": input_name.text().strip(),
            "max_amount": float(input_max.value()),
            "interest_rate": float(input_rate.value()),
            "duration_months": int(input_duration.value()),
        }

    def _add_loan_product(self) -> None:
        ok, payload = self._open_product_dialog("Add Loan Product")
        if not ok:
            return

        success, message = add_loan_product(
            self.db_path,
            payload.get("name", ""),
            float(payload.get("max_amount", 0.0)),
            float(payload.get("interest_rate", 0.0)),
            int(payload.get("duration_months", 1)),
        )
        if not success:
            QMessageBox.warning(self, "Could Not Save", message)
            return

        self._load_loan_products_table()
        self.settings_changed.emit()
        QMessageBox.information(self, "Saved", message)

    def _edit_loan_product(self) -> None:
        product_id = self._get_selected_product_id()
        if product_id <= 0:
            QMessageBox.warning(self, "No Selection", "Select a loan product to edit.")
            return

        selected_row = self.table_loan_products.selectionModel().selectedRows()[0].row()
        initial = {
            "name": self.table_loan_products.item(selected_row, 0).text() if self.table_loan_products.item(selected_row, 0) else "",
            "max_amount": float((self.table_loan_products.item(selected_row, 1).text() if self.table_loan_products.item(selected_row, 1) else "0").replace("₦", "").replace(",", "")),
            "interest_rate": float((self.table_loan_products.item(selected_row, 2).text() if self.table_loan_products.item(selected_row, 2) else "0").replace("%", "")),
            "duration_months": int((self.table_loan_products.item(selected_row, 3).text() if self.table_loan_products.item(selected_row, 3) else "1").replace(" months", "")),
        }

        ok, payload = self._open_product_dialog("Edit Loan Product", initial)
        if not ok:
            return

        success, message = update_loan_product(
            self.db_path,
            product_id,
            payload.get("name", ""),
            float(payload.get("max_amount", 0.0)),
            float(payload.get("interest_rate", 0.0)),
            int(payload.get("duration_months", 1)),
        )
        if not success:
            QMessageBox.warning(self, "Could Not Update", message)
            return

        self._load_loan_products_table()
        self.settings_changed.emit()
        QMessageBox.information(self, "Updated", message)

    def _toggle_loan_product_status(self) -> None:
        product_id = self._get_selected_product_id()
        if product_id <= 0:
            QMessageBox.warning(self, "No Selection", "Select a loan product to activate/deactivate.")
            return

        selected_row = self.table_loan_products.selectionModel().selectedRows()[0].row()
        status_item = self.table_loan_products.item(selected_row, 4)
        is_active_now = bool(status_item and status_item.text().strip().lower() == "active")
        target_active = not is_active_now

        success, message = set_loan_product_active(self.db_path, product_id, target_active)
        if not success:
            QMessageBox.warning(self, "Could Not Update", message)
            return

        self._load_loan_products_table()
        self.settings_changed.emit()
        QMessageBox.information(self, "Updated", message)

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
            'society_name': self.input_society_name.text().strip(),
            'address': self.input_address.text().strip(),
            'street': self.input_address.text().strip(),
            'city_state': self.input_city_state.text().strip(),
            'phone': self.input_phone.text().strip(),
            'email': self.input_email.text().strip(),
            'loan_multiplier': round(self.input_loan_multiplier.value(), 2),
            'min_monthly_saving': round(self.input_min_monthly_saving.value(), 2),
            'default_interest_rate': round(self.input_default_interest.value(), 2),
            'default_duration': int(self.input_default_duration.value()),
            'updated_at': datetime.now().isoformat(timespec='seconds'),
        }

        if new_cred and mode in ("pin", "password"):
            data['auth_hash'] = hash_credential(new_cred)
        if self.pending_recovery_key:
            data['recovery_key_hash'] = hash_credential(self.pending_recovery_key)

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
            if self.pending_recovery_key:
                key_plain = self.pending_recovery_key
                self.pending_recovery_key = ""
                QMessageBox.information(
                    self,
                    "Saved",
                    "Settings applied successfully.\n\n"
                    "New Recovery Key (save securely):\n"
                    f"{key_plain}",
                )
            else:
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
