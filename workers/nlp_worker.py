"""
NLPWorker — background spaCy processing (LLR-10, LLR-11, LLR-12, LLR-13)

Runs the spaCy French pipeline in a QThreadPool worker thread.
Results are delivered to the main thread via Qt signals only.
"""

from PyQt6.QtCore import QRunnable, QObject, pyqtSignal
import threading


class WorkerSignals(QObject):
    """
    Qt signals must be defined on a QObject subclass.
    QRunnable itself cannot own signals.
    """
    finished = pyqtSignal(int, object)   # (page_index, spaCy Doc)
    error    = pyqtSignal(int, str)      # (page_index, error message)


class NLPWorker(QRunnable):
    """
    Executes spaCy NLP on the given text in a background thread.

    Args:
        nlp:        The loaded spaCy Language pipeline object.
        text:       Raw French text to process.
        page_index: Page number being analyzed (echoed in the finished signal
                    so the Controller can match results to the right page).
    """

    def __init__(self, nlp, text: str, page_index: int):
        super().__init__()
        self.nlp         = nlp
        self.text        = text
        self.page_index  = page_index
        self.signals     = WorkerSignals()
        self._cancel_evt = threading.Event()

    def cancel(self) -> None:
        """Signal the worker to abort before or during processing (LLR-13)."""
        self._cancel_evt.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_evt.is_set()

    def run(self) -> None:
        """
        Called by QThreadPool on a background thread.
        NEVER call this directly from the main thread.
        """
        if self.is_cancelled:
            return
        try:
            doc = self.nlp(self.text)
            if not self.is_cancelled:
                self.signals.finished.emit(self.page_index, doc)
        except Exception as exc:
            self.signals.error.emit(self.page_index, str(exc))
