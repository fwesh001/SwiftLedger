"""
About page for SwiftLedger.
Shows software info, developer section, and FAQ accordion.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QScrollArea, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


# ── Collapsible FAQ widget ───────────────────────────────────────────

class _CollapsibleFAQ(QWidget):
    """A single question/answer that can be expanded or collapsed."""

    def __init__(self, question: str, answer: str):
        super().__init__()
        self._expanded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Question bar
        self.btn = QLabel(f"▶  {question}")
        self.btn.setStyleSheet(
            "QLabel { background: #2b2b2b; padding: 10px 14px; "
            "border: 1px solid #444; border-radius: 4px; font-weight: bold; }"
        )
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.mousePressEvent = lambda _: self.toggle()
        layout.addWidget(self.btn)

        # Answer area (hidden by default)
        self.answer_label = QLabel(answer)
        self.answer_label.setWordWrap(True)
        self.answer_label.setStyleSheet(
            "QLabel { background: #333; padding: 10px 14px; "
            "border: 1px solid #444; border-top: none; border-radius: 0 0 4px 4px; }"
        )
        self.answer_label.setVisible(False)
        layout.addWidget(self.answer_label)

        self._question = question

    def toggle(self) -> None:
        self._expanded = not self._expanded
        self.answer_label.setVisible(self._expanded)
        arrow = "▼" if self._expanded else "▶"
        self.btn.setText(f"{arrow}  {self._question}")


# ── About page ───────────────────────────────────────────────────────

class AboutPage(QWidget):
    """Software info, developer bio, and FAQ accordion."""

    def __init__(self, db_path: str = "swiftledger.db"):
        super().__init__()
        self.db_path = db_path
        self._build_ui()

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

        # ── Software info ────────────────────────────────────────────
        info_group = QGroupBox("Software Information")
        info_group.setFont(QFont("Arial", 12))
        info_layout = QVBoxLayout(info_group)

        logo_label = QLabel("[ SwiftLedger Logo ]")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet(
            "QLabel { font-size: 28px; font-weight: bold; color: #3498db; "
            "padding: 20px; border: 2px dashed #3498db; border-radius: 10px; }"
        )
        info_layout.addWidget(logo_label)

        version = QLabel("SwiftLedger v1.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet("font-size: 18px; font-weight: bold; color: #ecf0f1;")
        info_layout.addWidget(version)

        tagline = QLabel("Transparent. Simple. Secure.")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setStyleSheet("font-size: 13px; color: #bdc3c7; font-style: italic;")
        info_layout.addWidget(tagline)

        main.addWidget(info_group)

        # ── Developer section ────────────────────────────────────────
        dev_group = QGroupBox("About the Developer")
        dev_group.setFont(QFont("Arial", 12))
        dev_layout = QVBoxLayout(dev_group)

        dev_text = QLabel(
            "I built SwiftLedger to bring transparency and simplicity to society "
            "management. Every feature — from SHA-256 credential hashing to "
            "automatic dividend calculations — was designed with your organisation's "
            "trust in mind.\n\n"
            "For support or custom features, contact me at:\n"
            "📧  zabdielfwesh001@gmail.com\n"
            "🔗  github.com/fwesh001"
        )
        dev_text.setWordWrap(True)
        dev_text.setStyleSheet("font-size: 13px; line-height: 1.6; padding: 10px;")
        dev_layout.addWidget(dev_text)

        signature = QLabel("— Zabdiel, Developer")
        signature.setAlignment(Qt.AlignmentFlag.AlignRight)
        signature.setStyleSheet("font-size: 12px; font-style: italic; color: #7f8c8d; padding-right: 14px;")
        dev_layout.addWidget(signature)

        main.addWidget(dev_group)

        # ── FAQ accordion ────────────────────────────────────────────
        faq_group = QGroupBox("Frequently Asked Questions")
        faq_group.setFont(QFont("Arial", 12))
        faq_layout = QVBoxLayout(faq_group)

        faqs = [
            (
                "How do I backup data?",
                "The app uses swiftledger.db — a single SQLite file. "
                "Simply copy this file to a USB drive, cloud folder, or external backup. "
                "Restoring is as easy as replacing the file."
            ),
            (
                "What happens if I forget my PIN?",
                "Contact the System Administrator or Zabdiel for recovery procedures. "
                "Recovery involves resetting the auth_hash in the system_settings table."
            ),
            (
                "Is my data secure?",
                "Yes. SwiftLedger uses SHA-256 hashing for credentials with per-user "
                "cryptographic salts. All data is stored locally on your machine — "
                "nothing is sent to external servers."
            ),
            (
                "Can I run SwiftLedger on multiple computers?",
                "Each installation uses its own local database file. To share data, "
                "copy swiftledger.db to the new machine. Concurrent multi-user access "
                "is not yet supported."
            ),
            (
                "How are dividends calculated?",
                "Projected interest is estimated at 12% of total outstanding loans. "
                "60% is allocated to members and 40% to the society reserve."
            ),
        ]

        for q, a in faqs:
            faq_layout.addWidget(_CollapsibleFAQ(q, a))

        faq_layout.addStretch()
        main.addWidget(faq_group)

        main.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
