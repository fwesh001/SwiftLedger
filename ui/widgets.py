# Custom PySide6 widgets

from PySide6.QtWidgets import QWidget, QHBoxLayout, QComboBox, QLineEdit
from PySide6.QtCore import Qt, Signal


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
        self.input_search = QLineEdit()
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
