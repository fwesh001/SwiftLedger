"""
Advanced charting widgets for SwiftLedger analytics dashboard.
"""

import io
import tempfile
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    from matplotlib.patches import Rectangle
    import matplotlib.patches as mpatches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    FigureCanvas = None
    Figure = None


class InteractiveMonthlyChart(QWidget):
    """
    Interactive stacked bar chart showing monthly Savings vs Loans trends.
    Supports range switching (6M, 12M, YTD) and bar click detection.
    """

    COLORS = {
        'savings': '#27ae60',  # Emerald Green
        'loans': '#ff6f61',    # Coral Red
        'bg': '#1e1e1e',       # Dark background
        'text': '#ecf0f1',     # Light text
    }

    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self.months_range = 12
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Range selector
        range_layout = QHBoxLayout()
        range_label = QLabel("Range:")
        range_label.setFont(QFont("Arial", 10))

        btn_6m = QPushButton("6 Months")
        btn_6m.setMaximumWidth(100)
        btn_6m.clicked.connect(lambda: self._update_range(6))

        btn_12m = QPushButton("12 Months")
        btn_12m.setMaximumWidth(100)
        btn_12m.setStyleSheet("QPushButton { background-color: #3498db; }")
        btn_12m.clicked.connect(lambda: self._update_range(12))

        btn_ytd = QPushButton("Year-to-Date")
        btn_ytd.setMaximumWidth(100)
        btn_ytd.clicked.connect(self._update_ytd)

        range_layout.addWidget(range_label)
        range_layout.addWidget(btn_6m)
        range_layout.addWidget(btn_12m)
        range_layout.addWidget(btn_ytd)
        range_layout.addStretch()

        layout.addLayout(range_layout)

        # Chart container
        if MATPLOTLIB_AVAILABLE:
            self.fig = Figure(figsize=(10, 4), dpi=80, facecolor=self.COLORS['bg'])
            self.canvas = FigureCanvas(self.fig)
            self.canvas.mpl_connect('button_press_event', self._on_bar_click)
            layout.addWidget(self.canvas)
        else:
            placeholder = QLabel("Matplotlib not available")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(placeholder)

    def _update_range(self, months: int) -> None:
        self.months_range = months
        self._refresh_chart()

    def _update_ytd(self) -> None:
        today = date.today()
        jan_1 = date(today.year, 1, 1)
        days_elapsed = (today - jan_1).days
        self.months_range = max(1, days_elapsed // 30)
        self._refresh_chart()

    def _refresh_chart(self) -> None:
        if not MATPLOTLIB_AVAILABLE:
            return

        from logic.analytics import get_monthly_trend

        ok, trend = get_monthly_trend(self.db_path, self.months_range)
        if not ok or not trend:
            return

        self.fig.clear()
        ax = self.fig.add_subplot(111)

        months = trend.get('months', [])
        savings = trend.get('savings', [])
        loans = trend.get('loans', [])

        x_pos = range(len(months))
        bar_width = 0.6

        # Stacked bars
        bars_savings = ax.bar(x_pos, savings, bar_width, label='Savings', color=self.COLORS['savings'])
        bars_loans = ax.bar(x_pos, loans, bar_width, bottom=savings, label='Loans', color=self.COLORS['loans'])

        ax.set_xlabel('Month', color=self.COLORS['text'], fontsize=10)
        ax.set_ylabel('Amount (₦)', color=self.COLORS['text'], fontsize=10)
        ax.set_title('Monthly Savings vs Loans Trend', color=self.COLORS['text'], fontsize=12, fontweight='bold')
        ax.set_xticks(x_pos)
        ax.set_xticklabels(months, rotation=45, ha='right', color=self.COLORS['text'], fontsize=9)
        ax.tick_params(axis='y', colors=self.COLORS['text'])
        ax.set_facecolor(self.COLORS['bg'])
        ax.grid(axis='y', alpha=0.3, linestyle='--', color=self.COLORS['text'])
        ax.legend(facecolor=self.COLORS['bg'], edgecolor=self.COLORS['text'], labelcolor=self.COLORS['text'])

        # Store bar references for click detection
        self.bar_data = {
            'months': months,
            'savings': savings,
            'loans': loans,
            'bars_savings': bars_savings,
            'bars_loans': bars_loans,
        }

        self.fig.tight_layout()
        self.canvas.draw()

    def _on_bar_click(self, event) -> None:
        """Detect bar click and emit monthly snapshot dialog."""
        if event.inaxes is None or not hasattr(self, 'bar_data'):
            return

        x_clicked = event.xdata
        if x_clicked is None:
            return

        month_idx = int(round(x_clicked))
        if 0 <= month_idx < len(self.bar_data['months']):
            month_str = self.bar_data['months'][month_idx]
            self._show_monthly_insight(month_str)

    def _show_monthly_insight(self, month_str: str) -> None:
        """Open a full-screen dialog with detailed monthly metrics."""
        try:
            year, month = map(int, month_str.split('-'))
        except ValueError:
            return

        from logic.analytics import get_monthly_snapshot

        ok, snapshot = get_monthly_snapshot(self.db_path, year, month)
        if not ok:
            QMessageBox.warning(None, "Error", "Unable to load monthly snapshot.")
            return

        dialog = MonthlyInsightDialog(snapshot)
        dialog.exec()

    def capture_chart(self) -> str:
        """Save the current chart to a temporary PNG file."""
        if not MATPLOTLIB_AVAILABLE:
            return ""

        try:
            tmp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp_path = tmp_file.name
            tmp_file.close()
            self.fig.savefig(tmp_path, facecolor=self.COLORS['bg'], bbox_inches='tight', dpi=150)
            return tmp_path
        except Exception:
            return ""


class LTSRiskGauge(QWidget):
    """
    Circular speedometer gauge showing LTS Ratio.
    Green (0-60%), Amber (61-85%), Red (86%+).
    """

    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        if MATPLOTLIB_AVAILABLE:
            self.fig = Figure(figsize=(4, 3), dpi=80, facecolor='#1e1e1e')
            self.canvas = FigureCanvas(self.fig)
            layout.addWidget(self.canvas)
        else:
            placeholder = QLabel("Gauge unavailable")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(placeholder)

    def refresh_gauge(self, lts_ratio: float) -> None:
        """Update gauge with current LTS ratio."""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.fig.clear()
        ax = self.fig.add_subplot(111, projection='polar')

        # Gauge range: 0-100%
        theta = (lts_ratio / 100.0) * 180 if lts_ratio <= 100 else 180

        # Colors based on risk
        if lts_ratio <= 60:
            color = '#27ae60'  # Green
            status = 'Low Risk'
        elif lts_ratio <= 85:
            color = '#f39c12'  # Amber
            status = 'Medium Risk'
        else:
            color = '#e74c3c'  # Red
            status = 'High Risk'

        # Draw gauge
        theta_range = [0, 180]
        rad_range = [0, 1]

        ax.barh(0, 180, color='#34495e', alpha=0.3)
        ax.barh(0, theta, color=color, height=0.5)

        ax.set_ylim(rad_range)
        ax.set_xlim(theta_range)
        ax.set_yticklabels([])
        ax.set_xticklabels([])
        ax.spines['polar'].set_visible(False)

        # Add text label
        ax.text(90, 0.5, f"{lts_ratio:.1f}%\n{status}", ha='center', va='center',
                fontsize=12, fontweight='bold', color='#ecf0f1',
                bbox=dict(boxstyle='round', facecolor='#2b2b2b', alpha=0.8))

        self.fig.tight_layout()
        self.canvas.draw()


class MonthlyInsightDialog(QDialog):
    """Full-screen dialog showing detailed monthly financial metrics."""

    def __init__(self, snapshot: dict, parent: QWidget = None):
        super().__init__(parent)
        self.snapshot = snapshot
        self.setWindowTitle("Monthly Insight")
        self.setMinimumSize(600, 400)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel(f"Financial Snapshot: {self.snapshot.get('year')}-{self.snapshot.get('month', 1):02d}")
        title_font = QFont("Arial", 16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Metrics grid
        metrics = [
            ("Total Savings Growth", f"₦{self.snapshot.get('total_savings_growth', 0):,.2f}"),
            ("Lodgments", f"₦{self.snapshot.get('lodgments', 0):,.2f}"),
            ("Deductions", f"₦{self.snapshot.get('deductions', 0):,.2f}"),
            ("New Loans Disbursed", f"₦{self.snapshot.get('new_loans_disbursed', 0):,.2f}"),
            ("Total Interest Earned", f"₦{self.snapshot.get('total_interest_earned', 0):,.2f}"),
            ("Avg Interest Rate", f"{self.snapshot.get('avg_interest_rate', 0):.2f}%"),
        ]

        for label, value in metrics:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFont(QFont("Arial", 11))
            val = QLabel(value)
            val_font = QFont("Arial", 11)
            val_font.setBold(True)
            val.setFont(val_font)
            val.setStyleSheet("color: #27ae60;")
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            layout.addLayout(row)

        layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
