# SwiftLedger - Thrift Society Management Application
# Main entry point
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SwiftLedger")
        self.resize(800, 600)
        
        # Simple test label
        label = QLabel("Welcome to SwiftLedger", self)
        label.move(300, 300)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())