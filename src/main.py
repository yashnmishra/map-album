import sys
import os

# Add project root to sys.path so 'src' imports work when run as python src/main.py
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImageReader
from src.database.database_manager import DatabaseManager
from src.ui.main_window import MainWindow

def setup_theme(app: QApplication):
    app.setStyle("Fusion")
    
    qss = """
    /* Catppuccin Macchiato inspired Modern Dark Theme */
    QMainWindow {
        background-color: #24273a;
    }
    QWidget {
        color: #cad3f5;
        background-color: #24273a;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 13px;
    }
    QSplitter::handle {
        background-color: #363a4f;
    }
    QTreeWidget, QListWidget, QTextEdit, QLineEdit, QComboBox {
        background-color: #1e2030;
        border: 1px solid #363a4f;
        border-radius: 6px;
        padding: 6px;
        selection-background-color: #8aadf4;
        selection-color: #24273a;
    }
    QTreeWidget::item, QListWidget::item {
        padding: 4px;
        border-radius: 4px;
    }
    QTreeWidget::item:hover, QListWidget::item:hover {
        background-color: #363a4f;
    }
    QTreeWidget::item:selected, QListWidget::item:selected {
        background-color: #8aadf4;
        color: #1e2030;
    }
    QPushButton {
        background-color: #8aadf4;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        color: #1e2030;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #b7bdf8;
    }
    QPushButton:pressed {
        background-color: #7dc4e4;
    }
    QPushButton:disabled {
        background-color: #494d64;
        color: #8087a2;
    }
    QGroupBox {
        border: 1px solid #363a4f;
        border-radius: 8px;
        margin-top: 14px;
        padding-top: 14px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        color: #8aadf4;
        font-weight: bold;
    }
    QMenuBar {
        background-color: #1e2030;
        color: #cad3f5;
        border-bottom: 1px solid #363a4f;
    }
    QMenuBar::item {
        padding: 6px 10px;
        border-radius: 4px;
    }
    QMenuBar::item:selected {
        background-color: #363a4f;
    }
    QMenu {
        background-color: #1e2030;
        color: #cad3f5;
        border: 1px solid #363a4f;
        border-radius: 6px;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 24px;
        border-radius: 4px;
    }
    QMenu::item:selected {
        background-color: #8aadf4;
        color: #1e2030;
    }
    QScrollBar:vertical {
        border: none;
        background: #1e2030;
        width: 10px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background: #494d64;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background: #5b6078;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """
    app.setStyleSheet(qss)

def main():
    # Increase the QImage allocation limit to 1GB to support massive 140-megapixel images
    QImageReader.setAllocationLimit(1024)
    
    app = QApplication(sys.argv)
    setup_theme(app)
    
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    
    window = MainWindow(session)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    # Ensure current working directory is the project root, assuming main.py is in src/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    os.chdir(project_root)
    
    main()
