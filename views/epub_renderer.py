"""
EPUBRenderer — native EPUB chapter rendering (LLR-07, LLR-08, LLR-09)

Uses EbookLib to parse the EPUB spine and QWebEngineView (or QTextBrowser
fallback) to render each chapter's HTML content inside the PyQt6 GUI.
"""

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal

# Attempt to import QWebEngineView; fall back gracefully (LLR-09)
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    _WEB_ENGINE_AVAILABLE = True
except ImportError:
    from PyQt6.QtWidgets import QTextBrowser as _FallbackWidget
    _WEB_ENGINE_AVAILABLE = False


class EPUBRenderer(QWidget):
    """
    Renders EPUB chapters inside a native Qt widget.

    Prefers QWebEngineView for full CSS/HTML support (LLR-08).
    Falls back to QTextBrowser if PyQt6-WebEngine is not installed (LLR-09).

    Signals:
        chapter_text_ready(int, str): chapter index and its plain text for NLP.
        chapter_count_known(int):     emitted once when the EPUB is opened.
    """

    chapter_text_ready  = pyqtSignal(int, str)
    chapter_count_known = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chapters: list  = []   # list of EpubHtml items (the spine order)
        self._current_idx: int = 0
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        if _WEB_ENGINE_AVAILABLE:
            self.content_widget = QWebEngineView()           # LLR-08
        else:
            self.content_widget = _FallbackWidget()          # LLR-09
            self.content_widget.setReadOnly(True)

        root.addWidget(self.content_widget)

    # ── Public API ────────────────────────────────────────────────────────────

    def open_document(self, file_path: str) -> int:
        """
        Open an EPUB file, build the chapter list, and render chapter 0.

        Returns:
            Number of HTML chapters found, or 0 on failure.
        """
        try:
            book = epub.read_epub(file_path)                 # LLR-07
            # Collect HTML items in spine order
            self._chapters = [
                item for item in book.get_items()
                if item.get_type() == ebooklib.ITEM_DOCUMENT
            ]
            count = len(self._chapters)
            if count == 0:
                self._show_error("No readable chapters found in this EPUB.")
                return 0
            self.chapter_count_known.emit(count)
            self.render_chapter(0)
            return count
        except Exception as exc:
            self._show_error(f"Error opening EPUB:\n{exc}")
            return 0

    def render_chapter(self, chapter_index: int) -> None:
        """
        Render the given chapter and emit its plain text for NLP.
        """
        if not self._chapters or chapter_index < 0 or chapter_index >= len(self._chapters):
            return

        self._current_idx = chapter_index
        item = self._chapters[chapter_index]

        try:
            raw_bytes    = item.get_content()               # LLR-07: raw HTML bytes
            html_content = raw_bytes.decode("utf-8", errors="replace")
        except Exception as exc:
            self._show_error(f"Cannot decode chapter {chapter_index}: {exc}")
            return

        # Render HTML in the web view (LLR-08) or text browser (LLR-09)
        if _WEB_ENGINE_AVAILABLE:
            self.content_widget.setHtml(html_content)
        else:
            self.content_widget.setHtml(html_content)

        # Extract plain text for NLP (strip HTML tags)
        plain_text = self._html_to_text(html_content)
        self.chapter_text_ready.emit(chapter_index, plain_text)

    def close_document(self) -> None:
        self._chapters = []
        if _WEB_ENGINE_AVAILABLE:
            self.content_widget.setHtml("")
        else:
            self.content_widget.clear()

    @property
    def current_page(self) -> int:
        return self._current_idx

    @property
    def page_count(self) -> int:
        return len(self._chapters)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Strip HTML tags using BeautifulSoup4, returning clean plain text."""
        soup = BeautifulSoup(html, "lxml")
        return soup.get_text(separator=" ", strip=True)

    def _show_error(self, message: str) -> None:
        if _WEB_ENGINE_AVAILABLE:
            self.content_widget.setHtml(
                f"<p style='color:red;font-family:monospace'>{message}</p>"
            )
        else:
            self.content_widget.setPlainText(message)
