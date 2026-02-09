import sys
import os
from PySide6.QtWidgets import QApplication

# 1. Add the project directory to the path so Python finds your folders
base_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_path)

# 2. Import the REAL MainWindow from your ui folder
from ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 3. Launch the actual application
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())