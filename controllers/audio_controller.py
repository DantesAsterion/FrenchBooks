"""
AudioController — TTS synthesis queue and audio playback (LLR-31)

Manages AudioWorker dispatch, deduplication, and QMediaPlayer controls.
Exposes a clean signal/slot interface for the FlashcardManagerPanel.
"""

import hashlib
from PyQt6.QtCore import QObject, pyqtSignal, QThreadPool, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from workers.audio_worker import AudioWorker


class AudioController(QObject):
    """
    Singleton-style controller owned by MainWindow (one per application session).

    Signals:
        synthesis_done(text, path):   TTS file saved successfully.
        synthesis_error(text, msg):   TTS synthesis failed; audio_path stays empty.
        status_message(str):          Human-readable progress for the status bar.
        playback_state_changed(int):  Forwards QMediaPlayer.PlaybackState.
    """

    synthesis_done          = pyqtSignal(str, str)   # (sentence, mp3_path)
    synthesis_error         = pyqtSignal(str, str)   # (sentence, error_msg)
    status_message          = pyqtSignal(str)
    playback_state_changed  = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Active workers keyed by sentence hash to prevent duplicate synthesis
        self._active: dict[str, AudioWorker] = {}

        # Qt media player for local MP3 preview
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(1.0)
        self._player.playbackStateChanged.connect(
            lambda s: self.playback_state_changed.emit(int(s))
        )

    # ── Synthesis API ─────────────────────────────────────────────────────────

    def synthesize(self, text: str, output_path: str,
                   lang: str = "fr", slow: bool = False) -> None:
        """
        Enqueue a gTTS synthesis job if one is not already running for this text.
        Results arrive via synthesis_done / synthesis_error signals (LLR-31).
        """
        key = self._hash(text)
        if key in self._active:
            return   # already synthesizing this sentence; deduplicate

        worker = AudioWorker(text, output_path, lang=lang, slow=slow)
        worker.signals.finished.connect(self._on_done)
        worker.signals.error.connect(self._on_error)
        self._active[key] = worker
        QThreadPool.globalInstance().start(worker)
        self.status_message.emit(f"Synthesizing: {text[:50]}…")

    def cancel_all(self) -> None:
        """Cancel all in-flight synthesis workers."""
        for worker in self._active.values():
            worker.cancel()
        self._active.clear()

    # ── Playback API ──────────────────────────────────────────────────────────

    def play(self, file_path: str) -> None:
        """Load and play an MP3 file from disk."""
        self._player.setSource(QUrl.fromLocalFile(str(file_path)))
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()

    def set_playback_rate(self, rate: float) -> None:
        """
        Adjust playback speed. Common values: 0.5 (slow), 0.75, 1.0, 1.25, 1.5.
        QMediaPlayer supports the full float range.
        """
        self._player.setPlaybackRate(rate)

    def set_volume(self, volume: float) -> None:
        """Volume in range [0.0, 1.0]."""
        self._audio_output.setVolume(max(0.0, min(1.0, volume)))

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]

    def _on_done(self, text: str, path: str) -> None:
        key = self._hash(text)
        self._active.pop(key, None)
        self.synthesis_done.emit(text, path)
        self.status_message.emit(f"Audio ready: {path}")

    def _on_error(self, text: str, msg: str) -> None:
        key = self._hash(text)
        self._active.pop(key, None)
        self.synthesis_error.emit(text, msg)
        self.status_message.emit(f"Audio synthesis failed: {msg}")
