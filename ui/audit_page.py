"""
Audit Log page for SwiftLedger.
Displays system audit logs with search/filter, colour-coded status, and PDF export.
"""

import sys
from pathlib import Path
from datetime import datetime

from utils import get_export_path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QLineEdit, QComboBox, QMessageBox, QFileDialog,
    QDialog, QFormLayout, QTextEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QHeaderView

sys.path.insert(0, str(Path(__file__).parent.parent))
from database.queries import get_all_logs


class AuditLogPage(QWidget):
    """Full audit-log viewer with search, colour cues, and PDF export."""

    CATEGORY_ALIASES = {
        "member": "Registration",
        "members": "Registration",
        "registration": "Registration",
        "profile": "Registration",
        "profile update": "Registration",
        "savings": "Financial",
        "loans": "Financial",
        "loan": "Financial",
        "financial": "Financial",
        "report": "Financial",
        "reports": "Financial",
        "security": "Security",
        "settings": "System",
        "system": "System",
        "preference": "System",
        "preferences": "System",
    }

    CATEGORY_COLOURS = {
        "Registration": QColor("#27ae60"),
        "Security": QColor("#e74c3c"),
        "Financial": QColor("#3498db"),
        "System": QColor("#8e44ad"),
        "Unknown": QColor("#7f8c8d"),
    }

    STATUS_COLOURS = {
        "success": QColor("#27ae60"),
        "ok": QColor("#27ae60"),
        "failed": QColor("#e74c3c"),
        "failure": QColor("#e74c3c"),
        "error": QColor("#e74c3c"),
        "pending": QColor("#f39c12"),
        "warning": QColor("#f39c12"),
    }

    def __init__(self, db_path: str = "swiftledger.db"):
        super().__init__()
        self.db_path = db_path
        self.all_logs: list = []
        self._build_ui()
        self.refresh_logs()

    # ── UI ───────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(15, 15, 15, 15)
        main.setSpacing(12)

        # Title
        title = QLabel("Audit Logs")
        tf = QFont("Arial", 18)
        tf.setBold(True)
        title.setFont(tf)
        main.addWidget(title)

        # ── Search / Filter row ─────────────────────────────────────
        filter_row = QHBoxLayout()

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Search by user or description…")
        self.input_search.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.input_search)

        self.combo_category = QComboBox()
        self.combo_category.addItem("All Categories")
        self.combo_category.currentTextChanged.connect(self._apply_filter)
        filter_row.addWidget(self.combo_category)

        self.btn_refresh = QPushButton("⟳  Refresh")
        self.btn_refresh.setMinimumWidth(100)
        self.btn_refresh.setMinimumHeight(34)
        self.btn_refresh.clicked.connect(self.refresh_logs)
        filter_row.addWidget(self.btn_refresh)

        self.btn_export = QPushButton("Export Log to PDF")
        self.btn_export.setMinimumWidth(140)
        self.btn_export.setMinimumHeight(34)
        self.btn_export.clicked.connect(self.export_to_pdf)
        filter_row.addWidget(self.btn_export)

        main.addLayout(filter_row)

        # ── Table ───────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Timestamp", "User", "Category", "Description", "Status"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self._open_log_details_from_item)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 400)
        main.addWidget(self.table)

    # ── Data ─────────────────────────────────────────────────────────

    def refresh_logs(self) -> None:
        ok, logs = get_all_logs(self.db_path)
        if not ok:
            QMessageBox.critical(self, "Error", "Failed to load audit logs.")
            return

        self.all_logs = logs

        # Rebuild category combo while preserving selection
        prev = self.combo_category.currentText()
        categories = sorted(
            {
                self._canonical_category(str(log.get('category', '')))
                for log in logs
                if str(log.get('category', '')).strip()
            }
        )
        self.combo_category.blockSignals(True)
        self.combo_category.clear()
        self.combo_category.addItem("All Categories")
        self.combo_category.addItems(categories)
        idx = self.combo_category.findText(prev)
        if idx >= 0:
            self.combo_category.setCurrentIndex(idx)
        self.combo_category.blockSignals(False)

        self._apply_filter()

    def _apply_filter(self) -> None:
        search = self.input_search.text().strip().lower()
        cat_filter = self.combo_category.currentText()

        filtered = []
        for log in self.all_logs:
            canonical_category = self._canonical_category(str(log.get('category', '')))
            if cat_filter != "All Categories" and canonical_category != cat_filter:
                continue
            if search:
                haystack = f"{log.get('user', '')} {log.get('description', '')}".lower()
                if search not in haystack:
                    continue
            filtered.append(log)

        self._populate_table(filtered)

    def _populate_table(self, logs: list) -> None:
        self.table.setRowCount(0)
        for row_idx, log in enumerate(logs):
            self.table.insertRow(row_idx)

            ts = QTableWidgetItem(str(log.get('timestamp', '')))
            user = QTableWidgetItem(str(log.get('user', '')))
            canonical_category = self._canonical_category(str(log.get('category', '')))
            cat = QTableWidgetItem(canonical_category)
            desc = QTableWidgetItem(str(log.get('description', '')))
            status_text = str(log.get('status', ''))
            status = QTableWidgetItem(status_text)

            for item in (ts, user, cat, desc, status):
                item.setData(Qt.ItemDataRole.UserRole, log)

            category_colour = self._resolve_category_colour(canonical_category)
            if category_colour is not None:
                cat.setForeground(category_colour)

            status_colour = self._resolve_status_colour(status_text)
            if status_colour is not None:
                status.setForeground(status_colour)

            self.table.setItem(row_idx, 0, ts)
            self.table.setItem(row_idx, 1, user)
            self.table.setItem(row_idx, 2, cat)
            self.table.setItem(row_idx, 3, desc)
            self.table.setItem(row_idx, 4, status)

    @staticmethod
    def _normalize_key(value: str) -> str:
        return value.strip().lower()

    def _canonical_category(self, category: str) -> str:
        normalized = self._normalize_key(category)
        if not normalized:
            return "Unknown"
        return self.CATEGORY_ALIASES.get(normalized, category.strip().title())

    def _resolve_category_colour(self, category: str) -> QColor | None:
        return self.CATEGORY_COLOURS.get(category)

    def _resolve_status_colour(self, status: str) -> QColor | None:
        normalized = self._normalize_key(status)
        return self.STATUS_COLOURS.get(normalized)

    def _open_log_details_from_item(self, item: QTableWidgetItem) -> None:
        row = item.row()
        source_item = self.table.item(row, 0)
        if source_item is None:
            return

        log = source_item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(log, dict):
            return

        self._show_log_detail_dialog(log)

    def _show_log_detail_dialog(self, log: dict) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Audit Log Details")
        dialog.resize(720, 420)

        root = QVBoxLayout(dialog)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        log_id = QLabel(str(log.get("id", "")))
        timestamp = QLabel(str(log.get("timestamp", "")))
        user = QLabel(str(log.get("user", "")))
        category_value = self._canonical_category(str(log.get("category", "")))
        category = QLabel(category_value)
        status_text = str(log.get("status", ""))
        status = QLabel(status_text)

        category_colour = self._resolve_category_colour(category_value)
        if category_colour is not None:
            category.setStyleSheet(f"color: {category_colour.name()}; font-weight: 600;")

        status_colour = self._resolve_status_colour(status_text)
        if status_colour is not None:
            status.setStyleSheet(f"color: {status_colour.name()}; font-weight: 600;")

        description = QTextEdit()
        description.setReadOnly(True)
        description.setPlainText(str(log.get("description", "")))
        description.setMinimumHeight(180)

        form.addRow("Log ID:", log_id)
        form.addRow("Timestamp:", timestamp)
        form.addRow("User:", user)
        form.addRow("Category:", category)
        form.addRow("Status:", status)
        root.addLayout(form)

        desc_title = QLabel("Description")
        desc_font = QFont("Arial", 10)
        desc_font.setBold(True)
        desc_title.setFont(desc_font)
        root.addWidget(desc_title)
        root.addWidget(description)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        close_row.addWidget(close_btn)
        root.addLayout(close_row)

        dialog.exec()

    # ── PDF Export ───────────────────────────────────────────────────

    def export_to_pdf(self) -> None:
        if not self.all_logs:
            QMessageBox.warning(self, "No Data", "No logs to export.")
            return

        cat_text = self.combo_category.currentText()
        export_type = "System logs (pdf)" if cat_text in ["All Categories", "System"] else f"{cat_text} logs (pdf)"
        default_dir = get_export_path("Audit page", export_type)

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Audit Report", str(default_dir / "SwiftLedger_Audit_Report.pdf"),
            "PDF Files (*.pdf)"
        )
        if not path:
            return

        try:
            from fpdf import FPDF
        except ImportError:
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib import colors
                from reportlab.lib.styles import getSampleStyleSheet
                self._export_reportlab(path)
                return
            except ImportError:
                QMessageBox.critical(
                    self, "Missing Library",
                    "Install fpdf2 or reportlab:\n  pip install fpdf2"
                )
                return

        self._export_fpdf(path)

    def _export_fpdf(self, path: str) -> None:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # Header
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 12, "SwiftLedger System Audit Report", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(6)

        # Column headers
        col_widths = [36, 24, 24, 80, 22]
        headers = ["Timestamp", "User", "Category", "Description", "Status"]
        pdf.set_font("Helvetica", "B", 8)
        for w, h in zip(col_widths, headers):
            pdf.cell(w, 8, h, border=1, align="C")
        pdf.ln()

        # Rows
        pdf.set_font("Helvetica", "", 7)
        for log in self.all_logs:
            vals = [
                self._sanitize_pdf_text(str(log.get('timestamp', ''))[:19]),
                self._sanitize_pdf_text(str(log.get('user', ''))),
                self._sanitize_pdf_text(str(log.get('category', ''))),
                self._sanitize_pdf_text(str(log.get('description', ''))[:60]),
                self._sanitize_pdf_text(str(log.get('status', ''))),
            ]
            for w, v in zip(col_widths, vals):
                pdf.cell(w, 7, v, border=1)
            pdf.ln()

        # Footer
        pdf.ln(10)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 8, "Developed by Zabdiel (www.zabdiel.tech)  |  SwiftLedger v1.0", align="C")

        pdf.output(path)
        QMessageBox.information(self, "Exported", f"Report saved to:\n{path}")

    @staticmethod
    def _sanitize_pdf_text(text: str) -> str:
        """Replace characters not supported by core PDF fonts."""
        if not text:
            return ""
        return (
            text.replace("₦", "NGN ")
            .replace("—", "-")
            .replace("–", "-")
        )

    def _export_reportlab(self, path: str) -> None:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet

        doc = SimpleDocTemplate(path, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("SwiftLedger System Audit Report", styles["Title"]))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles["Normal"]
        ))
        elements.append(Spacer(1, 12))

        data = [["Timestamp", "User", "Category", "Description", "Status"]]
        for log in self.all_logs:
            data.append([
                str(log.get('timestamp', ''))[:19],
                str(log.get('user', '')),
                str(log.get('category', '')),
                str(log.get('description', ''))[:50],
                str(log.get('status', '')),
            ])

        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(
            "Developed by Zabdiel (www.zabdiel.tech)  |  SwiftLedger v1.0",
            styles["Normal"]
        ))

        doc.build(elements)
        QMessageBox.information(self, "Exported", f"Report saved to:\n{path}")
