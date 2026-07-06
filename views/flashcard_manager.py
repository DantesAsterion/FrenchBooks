"""
FlashcardManagerPanel — Dashboard tab for managing cloze-deletion cards (LLR-33)

Displays all generated flashcards, provides Export CSV, Delete, Synthesize Audio
buttons, and audio preview controls (Play, Pause, Stop, Speed).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QComboBox, QFrame, QSizePolicy, QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


_AUDIO_PENDING  = "Pending"
_AUDIO_READY    = "Ready"
_AUDIO_ERROR    = "Error"

_STATUS_COLORS = {
    _AUDIO_PENDING: "#fff3cd",
    _AUDIO_READY:   "#d4edda",
    _AUDIO_ERROR:   "#f8d7da",
}

CARD_COLS = ["Cloze Sentence", "Word", "Lemma", "Definition", "Audio", "Source"]


class FlashcardManagerPanel(QWidget):
    """
    All-in-one Flashcard Manager tab widget (LLR-33).

    Signals:
        synthesize_requested(int):  User clicked "Synthesize Audio"; carries card index.
        export_requested(str):      User confirmed a save path for CSV export.
        delete_requested(list):     User clicked Delete; carries list of row indices.
        play_requested(str):        User clicked Play; carries audio file path.
        pause_requested():          User clicked Pause.
        stop_requested():           User clicked Stop.
        speed_changed(float):       User changed speed dropdown; carries rate multiplier.
    """

    synthesize_requested = pyqtSignal(int)
    export_requested     = pyqtSignal(str)
    delete_requested     = pyqtSignal(list)
    play_requested       = pyqtSignal(str)
    pause_requested      = pyqtSignal()
    stop_requested       = pyqtSignal()
    speed_changed        = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._card_paths: list[str] = []   # parallel to table rows: audio path per card
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QLabel("Flashcard Manager")
        hf = QFont(); hf.setBold(True); hf.setPointSize(11)
        hdr.setFont(hf)
        root.addWidget(hdr)

        sub = QLabel(
            "Right-click any word in the Study Guide to add a cloze-deletion card."
        )
        sub.setStyleSheet("color: #666; font-size: 9pt;")
        root.addWidget(sub)

        # ── Cards table ───────────────────────────────────────────────────────
        self.table = QTableWidget(0, len(CARD_COLS))
        self.table.setHorizontalHeaderLabels(CARD_COLS)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(CARD_COLS)):
            self.table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeMode.ResizeToContents
            )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(180)
        root.addWidget(self.table, stretch=1)

        # ── Action buttons ────────────────────────────────────────────────────
        btn_bar = QHBoxLayout()
        self.synth_btn  = QPushButton("Synthesize Audio")
        self.export_btn = QPushButton("Export CSV…")
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.setStyleSheet("color: #c0392b;")
        for b in (self.synth_btn, self.export_btn, self.delete_btn):
            btn_bar.addWidget(b)
        btn_bar.addStretch()
        root.addLayout(btn_bar)

        self.synth_btn.clicked.connect(self._on_synthesize)
        self.export_btn.clicked.connect(self._on_export)
        self.delete_btn.clicked.connect(self._on_delete)

        # ── Separator ─────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(sep)

        # ── Audio preview controls (LLR-32) ───────────────────────────────────
        audio_bar = QHBoxLayout()

        self.play_btn  = QPushButton("▶ Play")
        self.pause_btn = QPushButton("⏸ Pause")
        self.stop_btn  = QPushButton("⏹ Stop")
        for b in (self.play_btn, self.pause_btn, self.stop_btn):
            b.setFixedWidth(80)
            audio_bar.addWidget(b)

        audio_bar.addSpacing(16)
        audio_bar.addWidget(QLabel("Speed:"))
        self.speed_box = QComboBox()
        self.speed_box.addItems(["0.5×", "0.75×", "1.0×", "1.25×", "1.5×"])
        self.speed_box.setCurrentIndex(2)   # default 1.0×
        self.speed_box.setFixedWidth(72)
        audio_bar.addWidget(self.speed_box)
        audio_bar.addStretch()

        self.audio_status_label = QLabel("No audio selected.")
        self.audio_status_label.setStyleSheet("color: #666; font-size: 9pt;")
        audio_bar.addWidget(self.audio_status_label)

        root.addLayout(audio_bar)

        self.play_btn.clicked.connect(self._on_play)
        self.pause_btn.clicked.connect(self.pause_requested)
        self.stop_btn.clicked.connect(self.stop_requested)
        self.speed_box.currentIndexChanged.connect(self._on_speed_changed)

    # ── Public API ────────────────────────────────────────────────────────────

    def add_card(self, word: str, lemma: str, cloze: str,
                 definition: str, source_file: str) -> None:
        """Append one card row to the table."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._card_paths.append("")   # audio not yet synthesized

        values = [cloze, word, lemma, definition, _AUDIO_PENDING, source_file]
        for col, val in enumerate(values):
            item = QTableWidgetItem(val)
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            if col == 4:
                item.setBackground(QColor(_STATUS_COLORS[_AUDIO_PENDING]))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, col, item)

    def mark_audio_ready(self, card_index: int, audio_path: str) -> None:
        """Update the Audio column for a card once synthesis completes."""
        if 0 <= card_index < self.table.rowCount():
            self._card_paths[card_index] = audio_path
            item = self.table.item(card_index, 4)
            if item:
                item.setText(_AUDIO_READY)
                item.setBackground(QColor(_STATUS_COLORS[_AUDIO_READY]))

    def mark_audio_error(self, card_index: int) -> None:
        if 0 <= card_index < self.table.rowCount():
            item = self.table.item(card_index, 4)
            if item:
                item.setText(_AUDIO_ERROR)
                item.setBackground(QColor(_STATUS_COLORS[_AUDIO_ERROR]))

    def clear(self) -> None:
        self.table.setRowCount(0)
        self._card_paths.clear()

    def card_count(self) -> int:
        return self.table.rowCount()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _on_synthesize(self) -> None:
        rows = self._selected_rows()
        if not rows:
            QMessageBox.information(self, "No Selection",
                                    "Select one or more cards to synthesize audio.")
            return
        for row in rows:
            self.synthesize_requested.emit(row)

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Anki CSV", "flashcards_export.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if path:
            self.export_requested.emit(path)

    def _on_delete(self) -> None:
        rows = self._selected_rows()
        if not rows:
            return
        confirm = QMessageBox.question(
            self, "Delete Cards",
            f"Delete {len(rows)} selected card(s)? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(rows)

    def _on_play(self) -> None:
        rows = self._selected_rows()
        if not rows:
            return
        path = self._card_paths[rows[0]] if rows[0] < len(self._card_paths) else ""
        if path:
            self.audio_status_label.setText(f"Playing: {path[-40:]}")
            self.play_requested.emit(path)
        else:
            self.audio_status_label.setText("No audio for this card. Synthesize first.")

    def _on_speed_changed(self, index: int) -> None:
        rates = [0.5, 0.75, 1.0, 1.25, 1.5]
        self.speed_changed.emit(rates[index])

    def _selected_rows(self) -> list[int]:
        return sorted(set(
            idx.row() for idx in self.table.selectedIndexes()
        ))

    # ── Bulk-delete helpers (called after delete_requested is handled) ─────────

    def remove_rows(self, indices: list[int]) -> None:
        """Remove rows in descending order to preserve indices during deletion."""
        for row in sorted(indices, reverse=True):
            self.table.removeRow(row)
            if row < len(self._card_paths):
                del self._card_paths[row]
