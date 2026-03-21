"""PyQt6 application entry point."""

import sys

from PyQt6.QtWidgets import QApplication

from mdownloader.gui_qt.style import APP_STYLE
from mdownloader.gui_qt.windows.home import HomeWindow


def run():
    app = QApplication(sys.argv)
    app.setApplicationName("Music Downloader")
    app.setStyleSheet(APP_STYLE)

    window = HomeWindow()
    window.show()

    sys.exit(app.exec())
