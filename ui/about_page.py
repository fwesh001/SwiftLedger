"""
About page for SwiftLedger.
Shows software info and help guidance.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox,
    QScrollArea, QFrame,
    QTabWidget, QStackedWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.widgets import HorizontalNavBar

# ── About page ───────────────────────────────────────────────────────

class AboutPage(QWidget):
    """Software info and tabbed help guide."""

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

        # ── Horizontal nav bar ─────────────────────────────────────
        self.nav_bar = HorizontalNavBar(["About", "Help"])
        main.addWidget(self.nav_bar)

        # ── Stacked content for the two tabs ────────────────────────
        self.stack = QStackedWidget()
        main.addWidget(self.stack)

        self._build_about_tab()
        self._build_help_tab()

        self.nav_bar.currentChanged.connect(self.stack.setCurrentIndex)

        main.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ── Tab: About ─────────────────────────────────────────────────

    def _build_about_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(20)

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

        layout.addWidget(info_group)

        # ── About SwiftLedger ──────────────────────────────────────
        about_group = QGroupBox("About SwiftLedger")
        about_group.setFont(QFont("Arial", 12))
        about_layout = QVBoxLayout(about_group)

        about_text = QLabel(
            "SwiftLedger helps savings groups and cooperatives manage member "
            "records, contributions, loans, and dividends in one secure desktop "
            "app. It is built to keep bookkeeping transparent, reduce manual "
            "errors, and make day-to-day financial tracking simpler for "
            "administrators and members."
        )
        about_text.setWordWrap(True)
        about_text.setStyleSheet("font-size: 13px; line-height: 1.6; padding: 10px;")
        about_layout.addWidget(about_text)

        layout.addWidget(about_group)

        # ── About the Developer ─────────────────────────────────────
        dev_group = QGroupBox("About the Developer")
        dev_group.setFont(QFont("Arial", 12))
        dev_layout = QVBoxLayout(dev_group)

        dev_text = QLabel(
            "I built SwiftLedger to bring transparency and simplicity to society "
            "management. Every feature — from credential hashing to automatic "
            "dividend calculations — was designed with your organisation's trust in mind.\n\n"
            "For support or custom features, contact me at:\n"
            "📧  zabdielfwesh001@gmail.com\n"
            "🔗  github.com/fwesh001\n"
            "🌐  www.zabdiel.tech"
        )
        dev_text.setWordWrap(True)
        dev_text.setStyleSheet("font-size: 13px; line-height: 1.6; padding: 10px;")
        dev_layout.addWidget(dev_text)

        signature = QLabel("— Zabdiel, Developer  |  www.zabdiel.tech")
        signature.setAlignment(Qt.AlignmentFlag.AlignRight)
        signature.setStyleSheet("font-size: 12px; font-style: italic; color: #7f8c8d; padding-right: 14px;")
        dev_layout.addWidget(signature)

        layout.addWidget(dev_group)
        layout.addStretch()

        self.stack.addWidget(tab)

    # ── Tab: Help ──────────────────────────────────────────────────

    def _build_help_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(20)

        # ── Help tabs ────────────────────────────────────────────────
        help_group = QGroupBox("Help")
        help_group.setFont(QFont("Arial", 12))
        help_layout = QVBoxLayout(help_group)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        def make_help_tab(title: str, what_text: str, steps: list[str], advanced_note: str) -> QWidget:
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            tab_layout.setContentsMargins(12, 12, 12, 12)
            tab_layout.setSpacing(10)

            lbl_title = QLabel(title)
            lbl_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            tab_layout.addWidget(lbl_title)

            lbl_what = QLabel(f"What it is:\n{what_text}")
            lbl_what.setWordWrap(True)
            tab_layout.addWidget(lbl_what)

            steps_text = "\n".join(f"{idx + 1}. {step}" for idx, step in enumerate(steps))
            lbl_how = QLabel(f"How to use:\n{steps_text}")
            lbl_how.setWordWrap(True)
            tab_layout.addWidget(lbl_how)

            lbl_note = QLabel(f"Advanced note:\n{advanced_note}")
            lbl_note.setWordWrap(True)
            tab_layout.addWidget(lbl_note)

            tab_layout.addStretch()
            return tab

        tabs.addTab(
            make_help_tab(
                "Members",
                "Registers, edits, and tracks members with their banking and profile details.",
                [
                    "Open Members page and fill Staff ID, full name, phone, bank, account number, department, and date joined.",
                    "Click Register Member to save.",
                    "Use the search bar to find members quickly.",
                    "Double-click any member row to open full profile details.",
                ],
                "Use Download Template and Import Members for bulk onboarding when data is large.",
            ),
            "Members",
        )

        tabs.addTab(
            make_help_tab(
                "Loans",
                "Handles loan eligibility checks, disbursement, repayment tracking, and dashboard summaries.",
                [
                    "Search and select a member in Loans.",
                    "Enter principal, loan plan, rate, and duration.",
                    "Click Validate Loan and then Preview Schedule.",
                    "Submit Loan only after validation passes.",
                ],
                "Use the Repayment Status Dashboard filters (scope/status/date) before posting repayments.",
            ),
            "Loans",
        )

        tabs.addTab(
            make_help_tab(
                "Savings",
                "Posts savings transactions and displays running balances with recent history.",
                [
                    "Search and select a member on the Savings page.",
                    "Enter amount and choose transaction type and payment mode.",
                    "Add transfer reference when mode is Bank Transfer.",
                    "Click Post Saving to record the transaction.",
                ],
                "Salary Deduction mode auto-aligns transaction type to Deposit (+) for safer entry.",
            ),
            "Savings",
        )

        tabs.addTab(
            make_help_tab(
                "Reports",
                "Generates branded member statements, society summaries, and quick-start guides.",
                [
                    "Choose report scope (member or society).",
                    "Set date range and required options.",
                    "Preview report in-app where available.",
                    "Export PDF to save a final report copy.",
                ],
                "Use refreshed date bounds before export if recent data was just entered.",
            ),
            "Reports",
        )

        tabs.addTab(
            make_help_tab(
                "Audit",
                "Shows action history for security, member changes, savings, loans, and settings updates.",
                [
                    "Open Audit Logs from the sidebar.",
                    "Filter by category/date where needed.",
                    "Review action, status, and timestamps.",
                    "Export logs when compliance evidence is required.",
                ],
                "Use audit exports for month-end controls and review meetings.",
            ),
            "Audit",
        )

        tabs.addTab(
            make_help_tab(
                "Settings",
                "Controls theme, text scale, organization policy, loan products, and security credentials.",
                [
                    "Open Settings and choose the relevant tab.",
                    "Adjust appearance and text scale first for comfort.",
                    "Update organization details and loan defaults/products.",
                    "Click Apply to save and broadcast updates across pages.",
                ],
                "After changing loan defaults, refresh Loans page to confirm current values are reloaded.",
            ),
            "Settings",
        )

        help_layout.addWidget(tabs)
        layout.addWidget(help_group)
        layout.addStretch()

        self.stack.addWidget(tab)
