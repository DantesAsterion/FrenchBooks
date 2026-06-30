"""
PDFRenderer — native PDF page rendering (LLR-04, LLR-05, LLR-06)

Converts PDF pages to QPixmap using PyMuPDF and displays them
in a scrollable QLabel. Emits page_text_ready when raw text is extracted.
"""

import fitz  # PyMuPDF
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QSizePolicy
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal


# Default DPI scaling: 1.5 × 72 DPI = 108 DPI (LLR-04)
DEFAULT_ZOOM = 1.5


class PDFRenderer(QWidget):
    """
    Renders a single PDF page as a native QPixmap image.

    Signals:
        page_text_ready(int, str): page index and its extracted plain text,
            emitted after each render so the Controller can dispatch NLP.
        page_count_known(int):     emitted once when the document is opened.
    """

    page_text_ready = pyqtSignal(int, str)
    page_count_known = pyqtSignal(int)

    def __init__(self, zoom: float = DEFAULT_ZOOM, parent=None):
        super().__init__(parent)
        self.zoom       = zoom
        self._doc       = None    # fitz.Document
        self._page_idx  = 0
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # QScrollArea allows panning large pages (LLR-06)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.scroll_area.setStyleSheet("background: #404040;")

        # QLabel holds the pixmap (LLR-05, LLR-06)
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.page_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.scroll_area.setWidget(self.page_label)

        root.addWidget(self.scroll_area)

    # ── Public API ────────────────────────────────────────────────────────────

    def open_document(self, file_path: str) -> int:
        """
        Open a PDF file and render page 0.

        Returns:
            Total page count, or 0 on failure.
        """
        try:
            self._doc = fitz.open(file_path)
            count = self._doc.page_count
            self.page_count_known.emit(count)
            self.render_page(0)
            return count
        except Exception as exc:
            self.page_label.setText(f"Error opening PDF:\n{exc}")
            return 0

    def render_page(self, page_index: int) -> None:
        """
        Render the given page and display it. Extract its text and emit
        page_text_ready for the NLP pipeline.
        """
        if not self._doc or page_index < 0 or page_index >= self._doc.page_count:
            return

        self._page_idx = page_index
        page = self._doc.load_page(page_index)

        # Step 1: render to raw pixel data (LLR-04)
        matrix  = fitz.Matrix(self.zoom, self.zoom)
        pixmap  = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)

        # Step 2: convert fitz.Pixmap → QImage → QPixmap (LLR-05)
        qt_image = QImage(
            pixmap.samples,
            pixmap.width,
            pixmap.height,
            pixmap.stride,
            QImage.Format.Format_RGB888
        )
        qt_pixmap = QPixmap.fromImage(qt_image)

        # Step 3: display in QLabel inside QScrollArea (LLR-06)
        self.page_label.setPixmap(qt_pixmap)
        self.page_label.resize(qt_pixmap.size())

        # Extract plain text for NLP
        text = page.get_text("text")
        self.page_text_ready.emit(page_index, text)

    def close_document(self) -> None:
        if self._doc:
            self._doc.close()
            self._doc = None
        self.page_label.clear()

    def set_zoom(self, zoom: float) -> None:
        """Re-render the current page at a different zoom level."""
        self.zoom = zoom
        self.render_page(self._page_idx)

    @property
    def current_page(self) -> int:
        return self._page_idx

    @property
    def page_count(self) -> int:
        return self._doc.page_count if self._doc else 0
