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
# DashboardController imported lazily inside set_controller to avoid circular import


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
        # analyze_requested is connected inside set_controller once the NLP engine is ready

        # Reader → MainWindow
        self.reader.close_reader.connect(
            lambda: self.stack.setCurrentIndex(PAGE_DASHBOARD)
        )

    def set_controller(self, controller) -> None:
        """Inject the controller after it is constructed (spaCy loaded)."""
        from controllers.dashboard_controller import DashboardController
        from controllers.audio_controller import AudioController
        from services.flashcard_service import FlashcardService

        self.controller = controller
        self.controller.status_message.connect(self.status_bar.showMessage)
        self.controller.nlp_result_ready.connect(self.reader.update_nlp_results)
        self.reader.page_text_ready.connect(self.controller.on_page_text_ready)
        self.reader.page_changed.connect(self.controller.on_page_changed)

        # Dashboard corpus analysis controller (LLR-17..20)
        self.dash_controller = DashboardController(
            controller.nlp, self.dashboard, parent=self
        )
        self.dash_controller.status_message.connect(self.status_bar.showMessage)
        self.dashboard.analyze_requested.connect(self._on_analyze_requested_wired)

        # Flashcard service and audio controller (HLR-08, HLR-09, HLR-10)
        self.flashcard_service = FlashcardService()
        self.audio_controller  = AudioController(parent=self)
        self.audio_controller.status_message.connect(self.status_bar.showMessage)
        self._wire_flashcard_signals()

        self.status_bar.showMessage("NLP engine ready.")

    def _wire_flashcard_signals(self) -> None:
        """Connect the StudyGuidePanel and FlashcardManagerPanel to service/audio layers."""
        fc_panel = self.dashboard.flashcard_panel

        # Study Guide → FlashcardService (LLR-32)
        self.reader.study_guide.add_to_flashcard_requested.connect(
            self._on_add_to_flashcard
        )

        # FlashcardManagerPanel → service/audio (LLR-33)
        fc_panel.synthesize_requested.connect(self._on_synthesize_card)
        fc_panel.export_requested.connect(self._on_export_csv)
        fc_panel.delete_requested.connect(self._on_delete_cards)

        # Audio preview controls → AudioController (LLR-32)
        fc_panel.play_requested.connect(self.audio_controller.play)
        fc_panel.pause_requested.connect(self.audio_controller.pause)
        fc_panel.stop_requested.connect(self.audio_controller.stop)
        fc_panel.speed_changed.connect(self.audio_controller.set_playback_rate)

        # AudioController → FlashcardManagerPanel
        self.audio_controller.synthesis_done.connect(self._on_audio_done)
        self.audio_controller.synthesis_error.connect(self._on_audio_error)

    def _on_analyze_requested_wired(self, file_path: str) -> None:
        if hasattr(self, "_active_model") and self._active_model:
            self.dash_controller.set_model(self._active_model)
        self.dash_controller.on_analyze_requested(file_path)

    def _on_add_to_flashcard(
        self, word: str, lemma: str, sentence: str, cloze: str
    ) -> None:
        """
        Slot connected to StudyGuidePanel.add_to_flashcard_requested (LLR-32).
        Creates the card and immediately shows it in the manager panel.
        """
        source = getattr(
            getattr(self, "_active_model", None), "file_path", ""
        )
        page = getattr(self.reader, "_current_page", 0)
        record = self.flashcard_service.add_card(
            word=word, lemma=lemma, sentence=sentence,
            cloze_sentence=cloze, source_file=source, page_index=page,
        )
        self.dashboard.flashcard_panel.add_card(
            word=record.word, lemma=record.lemma,
            cloze=record.cloze_sentence, definition=record.definition,
            source_file=record.source_file,
        )
        # Switch to Flashcards tab so the user sees the newly added card
        self.dashboard.tab_widget.setCurrentIndex(1)
        self.stack.setCurrentIndex(PAGE_DASHBOARD)
        self.status_bar.showMessage(
            f"Flashcard added: '{word}' — {len(self.flashcard_service)} card(s) total."
        )

    def _on_synthesize_card(self, card_index: int) -> None:
        cards = self.flashcard_service.get_cards()
        if card_index >= len(cards):
            return
        record = cards[card_index]
        output_path = str(self.flashcard_service.audio_path_for(record))
        self.audio_controller.synthesize(record.sentence, output_path)

    def _on_audio_done(self, text: str, path: str) -> None:
        """Match synthesized audio back to the correct card and update the table."""
        cards = self.flashcard_service.get_cards()
        for idx, card in enumerate(cards):
            if card.sentence == text:
                self.flashcard_service.update_audio_path(idx, path)
                self.dashboard.flashcard_panel.mark_audio_ready(idx, path)
                break

    def _on_audio_error(self, text: str, msg: str) -> None:
        cards = self.flashcard_service.get_cards()
        for idx, card in enumerate(cards):
            if card.sentence == text:
                self.dashboard.flashcard_panel.mark_audio_error(idx)
                break

    def _on_export_csv(self, path: str) -> None:
        try:
            self.flashcard_service.export_csv(path)
            self.status_bar.showMessage(
                f"Exported {len(self.flashcard_service)} cards to {path}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", str(exc))

    def _on_delete_cards(self, indices: list) -> None:
        for idx in sorted(indices, reverse=True):
            self.flashcard_service.delete_card(idx)
        self.dashboard.flashcard_panel.remove_rows(indices)

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

