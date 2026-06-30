"""
main.py — FrenchBooks application entry point

Boot sequence:
  1. Create QApplication
  2. Show MainWindow immediately (fast start)
  3. Load spaCy fr_core_news_md in background
  4. Inject ReaderController into MainWindow when model is ready
"""

import sys
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt, QRunnable, QThreadPool, QObject, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor

from views.main_window import MainWindow


# ── spaCy lazy loader ─────────────────────────────────────────────────────────

class _ModelSignals(QObject):
    ready = pyqtSignal(object)   # carries the loaded spaCy nlp object
    error = pyqtSignal(str)

class SpacyLoader(QRunnable):
    """Load fr_core_news_md off the main thread so the window shows instantly."""

    def __init__(self):
        super().__init__()
        self.signals = _ModelSignals()

    def run(self) -> None:
        try:
            import spacy
            nlp = spacy.load("fr_core_news_md")
            self.signals.ready.emit(nlp)
        except Exception as exc:
            self.signals.error.emit(str(exc))


# ── Application bootstrap ─────────────────────────────────────────────────────

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("FrenchBooks")
    app.setOrganizationName("AsterionDantes")

    # Show main window right away — controller injected after spaCy loads
    window = MainWindow()
    window.status_bar.showMessage("Loading French NLP model (fr_core_news_md)…")
    window.show()

    def on_nlp_ready(nlp):
        from controllers.reader_controller import ReaderController
        controller = ReaderController(nlp, parent=window)
        window.set_controller(controller)

    def on_nlp_error(msg):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            window,
            "NLP Model Error",
            f"Could not load 'fr_core_news_md'.\n\n{msg}\n\n"
            "Run: python -m spacy download fr_core_news_md"
        )

    loader = SpacyLoader()
    loader.signals.ready.connect(on_nlp_ready)
    loader.signals.error.connect(on_nlp_error)
    QThreadPool.globalInstance().start(loader)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
