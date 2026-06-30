"""
ReaderView — MVC View layer, Split-Screen Reader (LLR-02, HLR-02, HLR-03)

Left panel:  StudyGuidePanel (NLP results)
Right panel: DocumentRenderer (PDF/EPUB content) — populated by feature/native-readers
Navigation bar: Previous / Next page buttons + current page indicator
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QPushButton,
    QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from views.study_guide_panel import StudyGuidePanel


class DocumentRendererPlaceholder(QWidget):
    """
    Placeholder for the actual PDF/EPUB renderer.
    Replaced by the concrete renderer in feature/native-readers.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel(
            "Document renderer will appear here.\n"
            "(feature/native-readers)"
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #888; border: 1px dashed #aaa;")
        layout.addWidget(label)


class ReaderView(QWidget):
    """
    Split-screen reader window.

    Signals:
        page_changed(int):   Emitted when the user navigates to a new page.
                             The Controller listens and dispatches NLP.
        close_reader():      User clicked the back/close button.
    """

    page_changed  = pyqtSignal(int)
    close_reader  = pyqtSignal()

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

        # Divider line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)

        # Right — Document renderer (placeholder until native-readers branch)
        self.renderer_container = QWidget()
        rc_layout = QVBoxLayout(self.renderer_container)
        rc_layout.setContentsMargins(0, 0, 0, 0)
        self.renderer = DocumentRendererPlaceholder()
        rc_layout.addWidget(self.renderer)

        self.splitter.addWidget(self.renderer_container)
        self.splitter.setSizes([300, 700])

        root.addWidget(self.splitter, stretch=1)

    # ── Public API called by the MainWindow / Controller ──────────────────────

    def load_document(self, title: str, page_count: int) -> None:
        """Set document metadata and reset to page 0."""
        self._total_pages  = page_count
        self._current_page = 0
        self._update_nav()
        self.study_guide.clear()

    def set_renderer(self, renderer_widget: QWidget) -> None:
        """
        Replace the placeholder renderer with the real PDF/EPUB widget.
        Called by MainWindow after feature/native-readers supplies the widget.
        """
        layout = self.renderer_container.layout()
        layout.replaceWidget(self.renderer, renderer_widget)
        self.renderer.hide()
        self.renderer = renderer_widget

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
            self.page_changed.emit(self._current_page)

    def _on_next(self) -> None:
        if self._current_page < self._total_pages - 1:
            self._current_page += 1
            self._update_nav()
            self.page_changed.emit(self._current_page)

    def _update_nav(self) -> None:
        self.page_label.setText(
            f"Page {self._current_page + 1} / {self._total_pages}"
        )
        self.prev_btn.setEnabled(self._current_page > 0)
        self.next_btn.setEnabled(self._current_page < self._total_pages - 1)
