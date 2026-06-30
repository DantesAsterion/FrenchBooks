"""
MainWindow — top-level application window (LLR-02, HLR-05)

Hosts two primary views:
  1. DashboardView  — library and corpus analysis
  2. ReaderView     — split-screen document reader

A QStackedWidget switches between them.
The MainWindow wires View signals to Controller slots.
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QFileDialog,
    QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from views.dashboard_view import DashboardView
from views.reader_view import ReaderView
from models.document_model import DocumentModel, DocumentType


PAGE_DASHBOARD = 0
PAGE_READER    = 1


class MainWindow(QMainWindow):
    """
    Application shell.  Owns the two top-level views and the controller.
    The NLP pipeline is lazy-loaded on first use to keep startup fast.
    """

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller   # injected after spaCy loads; see main.py
        self._build_ui()
        self._wire_signals()
        self.setWindowTitle("FrenchBooks — Interactive French Reader")
        self.resize(1280, 820)

    def _build_ui(self) -> None:
        # Central stack
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.dashboard = DashboardView()
        self.reader    = ReaderView()

        self.stack.addWidget(self.dashboard)   # index 0
        self.stack.addWidget(self.reader)       # index 1
        self.stack.setCurrentIndex(PAGE_DASHBOARD)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Open a PDF or EPUB to begin.")

        # Menu bar
        self._build_menu()

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        open_action = QAction("&Open File…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file_dialog)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # View menu
        view_menu = menu_bar.addMenu("&View")

        lib_action = QAction("&Library Dashboard", self)
        lib_action.triggered.connect(lambda: self.stack.setCurrentIndex(PAGE_DASHBOARD))
        view_menu.addAction(lib_action)

        reader_action = QAction("&Open Reader", self)
        reader_action.triggered.connect(lambda: self.stack.setCurrentIndex(PAGE_READER))
        view_menu.addAction(reader_action)

    def _wire_signals(self) -> None:
        # Dashboard → MainWindow
        self.dashboard.open_file_requested.connect(self._open_file_dialog)
        self.dashboard.open_reader_requested.connect(self._switch_to_reader)
        self.dashboard.analyze_requested.connect(self._on_analyze_requested)

        # Reader → MainWindow
        self.reader.close_reader.connect(
            lambda: self.stack.setCurrentIndex(PAGE_DASHBOARD)
        )

    def set_controller(self, controller) -> None:
        """Inject the controller after it is constructed (spaCy loaded)."""
        self.controller = controller
        self.controller.status_message.connect(self.status_bar.showMessage)
        self.controller.nlp_result_ready.connect(self.reader.update_nlp_results)
        # page_text_ready carries the raw text the controller needs to run NLP
        self.reader.page_text_ready.connect(self.controller.on_page_text_ready)
        self.reader.page_changed.connect(self.controller.on_page_changed)
        self.status_bar.showMessage("NLP engine ready.")

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Book",
            "",
            "Books (*.pdf *.epub);;PDF Files (*.pdf);;EPUB Files (*.epub)"
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str) -> None:
        """
        Create a DocumentModel shell for the selected file and register it
        in the Dashboard. Full parsing happens in feature/native-readers.
        """
        ext = os.path.splitext(path)[1].lower()
        if ext not in (".pdf", ".epub"):
            QMessageBox.warning(self, "Unsupported Format",
                                f"Cannot open '{ext}' files.")
            return

        model           = DocumentModel()
        model.file_path = path
        model.doc_type  = DocumentType.PDF if ext == ".pdf" else DocumentType.EPUB
        model.title     = os.path.basename(path)

        self.dashboard.add_book(model.title, path)
        self.status_bar.showMessage(f"Opened: {model.title}")

        # Persist model reference for later use by native-readers renderer
        self._active_model = model
        if self.controller:
            self.controller.load_document(model)

    def _switch_to_reader(self, file_path: str) -> None:
        self.stack.setCurrentIndex(PAGE_READER)
        if hasattr(self, "_active_model"):
            if self.controller:
                self.controller.load_document(self._active_model)
            # open_document() handles renderer creation + first page render
            self.reader.open_document(
                self._active_model.file_path,
                self._active_model.doc_type
            )

    def _on_analyze_requested(self, file_path: str) -> None:
        self.status_bar.showMessage(
            "Full corpus analysis not yet implemented "
            "(feature/dynamic-nlp). Open the Reader for per-page analysis."
        )
