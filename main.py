import sys
import os
import sqlite3
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtGui import QIcon

# 1. Add the project directory to the path so Python finds your folders
base_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_path)

# 2. Import core UI flows
from database.db_init import init_db
from ui.login_screen import LoginScreen
from ui.main_window import MainWindow
from ui.wizard import FirstRunWizard
from utils import get_asset_path


class AppController:
    """Coordinates first-run wizard, login gate, and main window."""

    def __init__(self, app: QApplication, db_path: str = "swiftledger.db"):
        self.app = app
        self.db_path = db_path
        self.wizard = None
        self.login = None
        self.window = None

    def start(self) -> None:
        init_db(self.db_path)

        if self._settings_exist():
            self._show_login()
        else:
            self._show_wizard()

    def _settings_exist(self) -> bool:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM system_settings")
            return (cursor.fetchone()[0] or 0) > 0
        finally:
            conn.close()

    def _show_wizard(self) -> None:
        self.wizard = FirstRunWizard(db_path=self.db_path)
        self.wizard.finished.connect(self._on_wizard_finished)
        self.wizard.show()

    def _on_wizard_finished(self, result: int) -> None:
        if result != QDialog.DialogCode.Accepted:
            return
        if self.wizard is not None:
            self.wizard.close()
            self.wizard = None
        self._show_login()

    def _show_login(self) -> None:
        self.login = LoginScreen(db_path=self.db_path)
        self.login.login_successful.connect(self._on_login_success)
        self.login.show()

    def _on_login_success(self) -> None:
        if self.login is not None:
            self.login.close()
            self.login = None
        self.window = MainWindow(db_path=self.db_path)
        self.window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # ── Load global stylesheet from assets/ ─────────────────────────
    qss_path = get_asset_path(os.path.join("assets", "styles.qss"))
    if os.path.isfile(qss_path):
        with open(qss_path, "r", encoding="utf-8") as fh:
            app.setStyleSheet(fh.read())

    # ── Set application window icon ─────────────────────────────────
    icon_path = get_asset_path(os.path.join("assets", "app_icon.ico"))
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 3. Launch with first-run + auth gate
    controller = AppController(app)
    controller.start()
    
    sys.exit(app.exec())