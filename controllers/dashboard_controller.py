"""
DashboardController — corpus analysis orchestrator (HLR-01, LLR-17..20)

Listens for analyze_requested from DashboardView,
dispatches a CorpusWorker, and forwards results back to the View.
"""

import fitz
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

from PyQt6.QtCore import QObject, pyqtSignal, QThreadPool

from models.document_model import DocumentModel, DocumentType
from workers.corpus_worker import CorpusWorker
from views.heatmap_canvas import HeatmapCanvas


class DashboardController(QObject):
    """
    Manages corpus-level NLP for the Library Dashboard.

    Signals:
        status_message(str): forwarded to main window status bar.
        analysis_complete():  emitted when all views have been updated.
    """

    status_message    = pyqtSignal(str)
    analysis_complete = pyqtSignal()

    def __init__(self, nlp_pipeline, dashboard_view, parent=None):
        super().__init__(parent)
        self.nlp      = nlp_pipeline
        self.view     = dashboard_view
        self._worker  = None
        self._model   = None

    def set_model(self, model: DocumentModel) -> None:
        self._model = model

    def on_analyze_requested(self, file_path: str) -> None:
        """Slot wired to DashboardView.analyze_requested."""
        if self._worker:
            self._worker.cancel()

        page_texts = self._extract_all_page_texts(file_path)
        if not page_texts:
            self.status_message.emit("Could not extract text from document.")
            return

        self.status_message.emit(
            f"Analyzing corpus ({len(page_texts)} pages)… please wait."
        )

        worker = CorpusWorker(self.nlp, page_texts)
        worker.signals.finished.connect(self._on_analysis_done)
        worker.signals.progress.connect(self._on_progress)
        worker.signals.error.connect(self._on_error)
        self._worker = worker
        QThreadPool.globalInstance().start(worker)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_all_page_texts(self, file_path: str) -> list[str]:
        """Extract plain text from every page/chapter without caching."""
        texts = []
        try:
            if file_path.lower().endswith(".pdf"):
                with fitz.open(file_path) as doc:
                    for page in doc:
                        texts.append(page.get_text("text"))
            else:
                book = epub.read_epub(file_path)
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        raw = item.get_content().decode("utf-8", errors="replace")
                        texts.append(BeautifulSoup(raw, "lxml").get_text(" "))
        except Exception as exc:
            self.status_message.emit(f"Extraction error: {exc}")
        return texts

    def _on_progress(self, done: int, total: int) -> None:
        pct = int(done / total * 100) if total else 0
        self.status_message.emit(f"Corpus analysis: {done}/{total} pages ({pct}%)…")

    def _on_analysis_done(self, result) -> None:
        self._worker = None
        self.status_message.emit("Corpus analysis complete.")

        # Populate vocabulary table (LLR-20)
        self.view.populate_vocab(result.vocab)

        # Populate tense summary table (LLR-19)
        self.view.populate_tenses(result.tense_rows)

        # Embed heatmap (LLR-17, LLR-18)
        canvas = HeatmapCanvas(result.word_counts)
        self.view.replace_heatmap(canvas)

        self.analysis_complete.emit()

    def _on_error(self, message: str) -> None:
        self._worker = None
        self.status_message.emit(f"Corpus analysis failed: {message}")
