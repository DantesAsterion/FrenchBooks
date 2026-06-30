"""
ReaderView — MVC View layer, Split-Screen Reader (LLR-02, HLR-02, HLR-03)

Left panel:  StudyGuidePanel (NLP results)
Right panel: PDFRenderer or EPUBRenderer depending on document type
Navigation bar: Previous / Next page buttons + current page indicator
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QPushButton,
    QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from views.study_guide_panel import StudyGuidePanel
from views.pdf_renderer import PDFRenderer
from views.epub_renderer import EPUBRenderer
from models.document_model import DocumentType


class ReaderView(QWidget):
    """
    Split-screen reader window.

    Signals:
        page_changed(int):   Emitted when the user navigates to a new page.
                             The Controller listens and dispatches NLP.
        close_reader():      User clicked the back/close button.
    """

    page_changed     = pyqtSignal(int)
    page_text_ready  = pyqtSignal(int, str)   # (page_index, raw_text) → Controller
    close_reader     = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_page  = 0
        self._total_pages   = 0
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top navigation bar ────────────────────────────────────────────────
        nav_bar = QWidget()
        nav_bar.setFixedHeight(40)
        nav_bar.setStyleSheet("background: #2d2d2d; color: white;")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(8, 4, 8, 4)

        self.back_btn = QPushButton("← Library")
        self.back_btn.setStyleSheet("color: white; background: transparent; border: none;")
        self.back_btn.clicked.connect(self.close_reader)
        nav_layout.addWidget(self.back_btn)

        nav_layout.addStretch()

        self.prev_btn = QPushButton("◀ Prev")
        self.prev_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self._on_prev)
        self.prev_btn.setStyleSheet("color: white; background: #444; border-radius: 3px; padding: 4px 8px;")
        nav_layout.addWidget(self.prev_btn)

        self.page_label = QLabel("Page 0 / 0")
        self.page_label.setStyleSheet("color: white; margin: 0 12px;")
        nav_layout.addWidget(self.page_label)

        self.next_btn = QPushButton("Next ▶")
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self._on_next)
        self.next_btn.setStyleSheet("color: white; background: #444; border-radius: 3px; padding: 4px 8px;")
        nav_layout.addWidget(self.next_btn)

        nav_layout.addStretch()
        root.addWidget(nav_bar)

        # ── Split-screen body ─────────────────────────────────────────────────
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left — Study Guide
        self.study_guide = StudyGuidePanel()
        self.study_guide.setMinimumWidth(260)
        self.splitter.addWidget(self.study_guide)

        # Right — Native document renderer (PDF or EPUB, set via open_document)
        self.renderer_container = QWidget()
        rc_layout = QVBoxLayout(self.renderer_container)
        rc_layout.setContentsMargins(0, 0, 0, 0)
        # Renderer is None until open_document() is called
        self._renderer_widget = None

        self.splitter.addWidget(self.renderer_container)
        self.splitter.setSizes([300, 700])

        root.addWidget(self.splitter, stretch=1)

    # ── Public API called by the MainWindow / Controller ──────────────────────

    def open_document(self, file_path: str, doc_type: DocumentType) -> None:
        """
        Instantiate the correct renderer, open the document, and wire signals.
        """
        layout = self.renderer_container.layout()

        # Remove and destroy the previous renderer if one exists
        if self._renderer_widget is not None:
            layout.removeWidget(self._renderer_widget)
            self._renderer_widget.hide()
            self._renderer_widget.deleteLater()

        if doc_type == DocumentType.PDF:
            renderer = PDFRenderer()
            renderer.page_text_ready.connect(self._on_page_text_ready)
            renderer.page_count_known.connect(self._on_page_count_known)
            count = renderer.open_document(file_path)
        else:
            renderer = EPUBRenderer()
            renderer.chapter_text_ready.connect(self._on_page_text_ready)
            renderer.chapter_count_known.connect(self._on_page_count_known)
            count = renderer.open_document(file_path)

        self._renderer_widget = renderer
        layout.addWidget(renderer)
        renderer.show()

        self._total_pages  = count
        self._current_page = 0
        self._update_nav()
        self.study_guide.clear()

    def load_document(self, title: str, page_count: int) -> None:
        """Legacy slot — updates nav bar metadata without re-opening a file."""
        self._total_pages  = page_count
        self._current_page = 0
        self._update_nav()
        self.study_guide.clear()

    def update_nlp_results(self, page_index: int, doc) -> None:
        """
        Slot connected to ReaderController.nlp_result_ready.
        Only update the panel if the result matches the current page.
        """
        if page_index == self._current_page:
            self.study_guide.update_from_doc(doc)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _on_prev(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self._update_nav()
            self._render_current()
            self.page_changed.emit(self._current_page)

    def _on_next(self) -> None:
        if self._current_page < self._total_pages - 1:
            self._current_page += 1
            self._update_nav()
            self._render_current()
            self.page_changed.emit(self._current_page)

    def _render_current(self) -> None:
        """Tell the active renderer to display the current page."""
        if self._renderer_widget is None:
            return
        if isinstance(self._renderer_widget, PDFRenderer):
            self._renderer_widget.render_page(self._current_page)
        elif isinstance(self._renderer_widget, EPUBRenderer):
            self._renderer_widget.render_chapter(self._current_page)

    def _on_page_text_ready(self, page_index: int, text: str) -> None:
        """
        Forwarded from the renderer. The Controller needs the text to dispatch
        NLP. We relay via page_changed signal (Controller listens for this) but
        also store text in the model via the controller, so we emit a dedicated
        signal here.
        """
        self.page_text_ready.emit(page_index, text)

    def _on_page_count_known(self, count: int) -> None:
        self._total_pages = count
        self._update_nav()

    def _update_nav(self) -> None:
        self.page_label.setText(
            f"Page {self._current_page + 1} / {self._total_pages}"
        )
        self.prev_btn.setEnabled(self._current_page > 0)
        self.next_btn.setEnabled(self._current_page < self._total_pages - 1)
