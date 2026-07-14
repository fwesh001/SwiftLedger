# Custom PySide6 widgets

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox, QLineEdit, QPushButton, QButtonGroup,
)
from PySide6.QtCore import Qt, Signal


class HorizontalNavBar(QWidget):
    """
    Reusable horizontal navigation bar (segmented button bar).

    Features:
      - 10px+ corner padding on each button
      - bottom outline (accent) on the active button
      - hover effect
    Emits ``currentChanged`` with the selected index when a tab is chosen.
    """

    currentChanged = Signal(int)

    # Accent colour used for the active bottom outline / hover.
    ACCENT = "#3498db"

    def __init__(self, items: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self._buttons: list[QPushButton] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        for index, label in enumerate(items):
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setMinimumHeight(38)
            # 10px+ corner padding (left/right) and vertical padding.
            btn.setStyleSheet(self._button_stylesheet(False))
            self._group.addButton(btn, index)
            btn.clicked.connect(lambda _checked=False, idx=index: self._select(idx))
            self._buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()
        self._current = -1
        if self._buttons:
            self._select(0)

    # ── Styling ────────────────────────────────────────────────────

    def _button_stylesheet(self, active: bool) -> str:
        base = (
            "QPushButton {"
            "  background-color: transparent;"
            "  color: #bdc3c7;"
            "  border: none;"
            "  border-bottom: 3px solid transparent;"
            "  padding: 10px 16px;"  # ≥10px corner padding
            "  font-size: 13px;"
            "  font-weight: bold;"
            "}"
            "QPushButton:hover {"
            f"  color: {self.ACCENT};"
            f"  border-bottom: 3px solid {self.ACCENT};"
            "}"
        )
        if active:
            return (
                "QPushButton {"
                f"  background-color: transparent;"
                f"  color: {self.ACCENT};"
                f"  border: none;"
                f"  border-bottom: 3px solid {self.ACCENT};"
                "  padding: 10px 16px;"
                "  font-size: 13px;"
                "  font-weight: bold;"
                "}"
            )
        return base

    # ── Selection ──────────────────────────────────────────────────

    def _select(self, index: int) -> None:
        if index < 0 or index >= len(self._buttons):
            return
        if index == self._current:
            return
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)
            btn.setStyleSheet(self._button_stylesheet(i == index))
        self._current = index
        self.currentChanged.emit(index)

    def current_index(self) -> int:
        return self._current

    def set_current_index(self, index: int) -> None:
        self._select(index)


class UppercaseLineEdit(QLineEdit):
    """QLineEdit variant that forces uppercase text for consistent data entry."""

    def __init__(self, *args, force_uppercase: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self._force_uppercase = bool(force_uppercase)
        self.textChanged.connect(self._handle_text_changed)

    def set_force_uppercase(self, enabled: bool) -> None:
        self._force_uppercase = bool(enabled)

    def _handle_text_changed(self, text: str) -> None:
        if not self._force_uppercase:
            return
        upper_text = text.upper()
        if upper_text == text:
            return
        cursor_pos = self.cursorPosition()
        self.blockSignals(True)
        self.setText(upper_text)
        self.blockSignals(False)
        self.setCursorPosition(min(cursor_pos, len(upper_text)))


class SearchFilterWidget(QWidget):
    """
    Search bar with integrated dropdown filter.
    Allows users to search by All Fields (multi-field), Staff ID, Full Name, or Phone.
    Emits queryChanged signal when text changes.
    """
    
    queryChanged = Signal(str, str)  # (filter_type, query_text)
    
    FILTER_OPTIONS = {
        "All Fields": "all",
        "Staff ID": "staff_number",
        "Full Name": "full_name",
        "Phone": "phone",
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Build the integrated search widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Filter dropdown
        self.combo_filter = QComboBox()
        self.combo_filter.addItems(self.FILTER_OPTIONS.keys())
        self.combo_filter.setMaximumWidth(120)
        self.combo_filter.setToolTip("Select search field: All Fields, Staff ID, Full Name, or Phone")
        
        # Search input
        self.input_search = UppercaseLineEdit()
        self.input_search.setPlaceholderText("Search by Staff ID, Name, or Phone...")
        self.input_search.textChanged.connect(self._on_text_changed)
        
        layout.addWidget(self.combo_filter)
        layout.addWidget(self.input_search)
        self.setLayout(layout)
    
    def _on_text_changed(self, text: str) -> None:
        """Emit signal when search text changes."""
        filter_type = self.get_filter_type()
        self.queryChanged.emit(filter_type, text)
    
    def get_filter_type(self) -> str:
        """Get current filter type (e.g., 'all', 'staff_number', 'full_name', 'phone')."""
        selected = self.combo_filter.currentText()
        return self.FILTER_OPTIONS.get(selected, "all")
    
    def get_filter_display(self) -> str:
        """Get current filter display name (e.g., 'All Fields', 'Staff ID')."""
        return self.combo_filter.currentText()
    
    def get_query(self) -> str:
        """Get current search query text."""
        return self.input_search.text().strip()
    
    def set_query(self, text: str) -> None:
        """Set search query text programmatically."""
        self.input_search.setText(text)
    
    def clear(self) -> None:
        """Clear search input and reset to default filter."""
        self.input_search.clear()
        self.combo_filter.setCurrentIndex(0)  # Reset to "All Fields"
