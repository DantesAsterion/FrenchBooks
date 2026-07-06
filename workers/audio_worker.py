"""
AudioWorker — background TTS synthesis via gTTS (LLR-29, LLR-30)

Runs gTTS off the GUI thread; delivers results via Qt signals.
Network failures are caught and surfaced as error signals (LLR-30).
"""

import threading
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal


class AudioSignals(QObject):
    """
    Qt signals for AudioWorker cross-thread communication.
    Must live on a QObject subclass; QRunnable cannot own signals.
    """
    finished = pyqtSignal(str, str)   # (original_text, output_mp3_path)
    error    = pyqtSignal(str, str)   # (original_text, error_message)


class AudioWorker(QRunnable):
    """
    Synthesizes French TTS for a single sentence using gTTS.

    Args:
        text:        The French sentence to synthesize.
        output_path: Absolute path where the MP3 will be saved.
        lang:        BCP-47 language tag (default "fr").
        slow:        If True, gTTS uses a slower speech rate (default False).
    """

    def __init__(self, text: str, output_path: str,
                 lang: str = "fr", slow: bool = False):
        super().__init__()
        self.text        = text
        self.output_path = output_path
        self.lang        = lang
        self.slow        = slow
        self.signals     = AudioSignals()
        self._cancel     = threading.Event()

    def cancel(self) -> None:
        """Thread-safe cancellation; no-op if run() has already started gTTS."""
        self._cancel.set()

    def run(self) -> None:
        """
        Called by QThreadPool on a background thread (LLR-29).
        NEVER invoke directly from the GUI thread.
        """
        if self._cancel.is_set():
            return
        try:
            from gtts import gTTS                          # deferred import: avoids
            tts = gTTS(text=self.text, lang=self.lang,    # startup cost if gTTS not
                       slow=self.slow)                      # used in this session
            tts.save(self.output_path)

            if not self._cancel.is_set():
                self.signals.finished.emit(self.text, self.output_path)

        except Exception as exc:
            # LLR-30: any failure (network, gTTS API) surfaces as error signal.
            # The flashcard record remains valid; audio_path stays empty.
            if not self._cancel.is_set():
                self.signals.error.emit(self.text, str(exc))
