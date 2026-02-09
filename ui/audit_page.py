"""
Audit Log page for SwiftLedger.
Displays system audit logs with search/filter, colour-coded status, and PDF export.
"""

import sys
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QLineEdit, QComboBox, QMessageBox, QFileDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

sys.path.insert(0, str(Path(__file__).parent.parent))
from database.queries import get_all_logs


class AuditLogPage(QWidget):
    """Full audit-log viewer with search, colour cues, and PDF export."""

    # Colour mapping for status values
    STATUS_COLOURS = {
        'Failed':   QColor('#e74c3c'),  # Red
        'FAILURE':  QColor('#e74c3c'),
        'Security': QColor('#e74c3c'),
        'SECURITY': QColor('#e74c3c'),
        'Financial': QColor('#3498db'),  # Blue
        'FINANCIAL': QColor('#3498db'),
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
        self.btn_refresh.clicked.connect(self.refresh_logs)
        filter_row.addWidget(self.btn_refresh)

        self.btn_export = QPushButton("Export Log to PDF")
        self.btn_export.setMinimumWidth(140)
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
        self.table.horizontalHeader().setStretchLastSection(True)
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
        categories = sorted({log.get('category', '') for log in logs if log.get('category')})
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
            if cat_filter != "All Categories" and log.get('category', '') != cat_filter:
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
            cat = QTableWidgetItem(str(log.get('category', '')))
            desc = QTableWidgetItem(str(log.get('description', '')))
            status_text = str(log.get('status', ''))
            status = QTableWidgetItem(status_text)

            # Colour the status and category cells
            colour = self._resolve_colour(status_text, str(log.get('category', '')))
            if colour:
                status.setForeground(colour)
                cat.setForeground(colour)

            self.table.setItem(row_idx, 0, ts)
            self.table.setItem(row_idx, 1, user)
            self.table.setItem(row_idx, 2, cat)
            self.table.setItem(row_idx, 3, desc)
            self.table.setItem(row_idx, 4, status)

    def _resolve_colour(self, status: str, category: str) -> QColor | None:
        for key in (status, category):
            if key in self.STATUS_COLOURS:
                return self.STATUS_COLOURS[key]
        return None

    # ── PDF Export ───────────────────────────────────────────────────

    def export_to_pdf(self) -> None:
        if not self.all_logs:
            QMessageBox.warning(self, "No Data", "No logs to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Audit Report", "SwiftLedger_Audit_Report.pdf",
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
                str(log.get('timestamp', ''))[:19],
                str(log.get('user', '')),
                str(log.get('category', '')),
                str(log.get('description', ''))[:60],
                str(log.get('status', '')),
            ]
            for w, v in zip(col_widths, vals):
                pdf.cell(w, 7, v, border=1)
            pdf.ln()

        # Footer
        pdf.ln(10)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 8, "Developed by Zabdiel  |  SwiftLedger v1.0", align="C")

        pdf.output(path)
        QMessageBox.information(self, "Exported", f"Report saved to:\n{path}")

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
            "Developed by Zabdiel  |  SwiftLedger v1.0",
            styles["Normal"]
        ))

        doc.build(elements)
        QMessageBox.information(self, "Exported", f"Report saved to:\n{path}")
