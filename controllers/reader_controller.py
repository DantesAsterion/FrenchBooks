"""
ReaderController — MVC Controller layer (LLR-03)

Mediates between View events and the DocumentModel + NLPWorker.
Never imports PyQt6 widgets; communicates with View via signals only.
"""

from PyQt6.QtCore import QObject, pyqtSignal, QThreadPool
from models.document_model import DocumentModel
from workers.nlp_worker import NLPWorker


class ReaderController(QObject):
    """
    Listens for page-navigation events from the View, dispatches NLP workers,
    and forwards results back to the View via signals.

    Signals:
        nlp_result_ready(int, object): Emitted when NLP for a page is done.
            int   = page index
            object = spaCy Doc
        nlp_error(int, str):           Emitted if the NLP worker raises.
        status_message(str):           Human-readable status for the status bar.
    """

    nlp_result_ready = pyqtSignal(int, object)
    nlp_error        = pyqtSignal(int, str)
    status_message   = pyqtSignal(str)

    def __init__(self, nlp_pipeline, parent=None):
        super().__init__(parent)
        self.nlp             = nlp_pipeline
        self.model           = DocumentModel()
        self._active_worker  = None   # type: NLPWorker | None

    def load_document(self, model: DocumentModel) -> None:
        """Replace the current document model."""
        self.model = model
        self.status_message.emit(f"Loaded: {model.title} ({model.page_count} pages)")

    def on_page_text_ready(self, page_index: int, text: str) -> None:
        """
        Slot connected to ReaderView.page_text_ready.
        The renderer has extracted text from a page; store it and run NLP.
        """
        self.model.set_page_text(page_index, text)
        self._dispatch_nlp(page_index)

    def on_page_changed(self, page_index: int) -> None:
        """
        Called by the View's nav buttons (LLR-13).
        If text is already cached, dispatch NLP; otherwise the renderer will
        call on_page_text_ready when it finishes rendering.
        """
        if self.model.is_cached(page_index):
            cached_doc = self.model.get_page_nlp(page_index)
            self.nlp_result_ready.emit(page_index, cached_doc)

    def _dispatch_nlp(self, page_index: int) -> None:
        """Cancel any in-flight worker and start a new one for page_index."""
        if self._active_worker:
            self._active_worker.cancel()
            self._active_worker = None

        text = self.model.get_page_text(page_index)
        if not text:
            return

        self.status_message.emit(f"Analyzing page {page_index + 1}…")
        worker = NLPWorker(self.nlp, text, page_index)
        worker.signals.finished.connect(self._on_worker_finished)
        worker.signals.error.connect(self._on_worker_error)
        self._active_worker = worker
        QThreadPool.globalInstance().start(worker)

    def _on_worker_finished(self, page_index: int, doc: object) -> None:
        self.model.set_page_nlp(page_index, doc)
        self._active_worker = None
        self.nlp_result_ready.emit(page_index, doc)
        self.status_message.emit(f"Page {page_index + 1} analyzed.")

    def _on_worker_error(self, page_index: int, message: str) -> None:
        self._active_worker = None
        self.nlp_error.emit(page_index, message)
        self.status_message.emit(f"NLP error on page {page_index + 1}: {message}")
