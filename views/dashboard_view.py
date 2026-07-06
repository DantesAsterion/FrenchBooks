"""
DashboardView — MVC View layer, Library Dashboard (LLR-02, HLR-01)

Displays loaded books and corpus-level NLP analysis results.
Heatmap, tense summary, and vocabulary list are populated by the Controller
after corpus analysis is complete.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QFrame, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from views.flashcard_manager import FlashcardManagerPanel


class DashboardView(QWidget):
    """
    Library dashboard — left side shows the book list, right side shows
    corpus-level NLP analysis for the selected book.

    Signals:
        open_file_requested():  User clicked "Open File".
        book_selected(str):     User double-clicked a book; carries file path.
        analyze_requested(str): User clicked "Analyze"; carries file path.
        open_reader_requested(str): User clicked "Read"; carries file path.
    """

    open_file_requested   = pyqtSignal()
    book_selected         = pyqtSignal(str)
    analyze_requested     = pyqtSignal(str)
    open_reader_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_map: dict[str, str] = {}   # display_name -> file_path
        self._build_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        # ── Left: book list ──────────────────────────────────────────────────
        left = QWidget()
        left.setFixedWidth(220)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Library")
        hf = QFont(); hf.setBold(True); hf.setPointSize(12)
        header.setFont(hf)
        left_layout.addWidget(header)

        self.open_btn = QPushButton("Open File…")
        self.open_btn.clicked.connect(self.open_file_requested)
        left_layout.addWidget(self.open_btn)

        self.book_list = QListWidget()
        self.book_list.itemDoubleClicked.connect(self._on_book_double_clicked)
        left_layout.addWidget(self.book_list)

        root.addWidget(left)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(sep)

        # ── Right: tab widget containing Analysis + Flashcards ─────────────────
        right_container = QWidget()
        rc_layout = QVBoxLayout(right_container)
        rc_layout.setContentsMargins(0, 0, 0, 0)

        # Action bar (above the tabs, always visible)
        action_bar = QWidget()
        ab_layout = QHBoxLayout(action_bar)
        ab_layout.setContentsMargins(0, 0, 0, 4)
        self.book_title_label = QLabel("Select a book from the library.")
        tf = QFont(); tf.setItalic(True)
        self.book_title_label.setFont(tf)
        ab_layout.addWidget(self.book_title_label, stretch=1)
        self.analyze_btn = QPushButton("Analyze Corpus")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        ab_layout.addWidget(self.analyze_btn)
        self.read_btn = QPushButton("Open Reader")
        self.read_btn.setEnabled(False)
        self.read_btn.clicked.connect(self._on_read_clicked)
        ab_layout.addWidget(self.read_btn)
        rc_layout.addWidget(action_bar)

        # Tab widget
        self.tab_widget = QTabWidget()

        # ── Tab 1: Corpus Analysis ────────────────────────────────────────────
        analysis_tab = QWidget()
        at_layout = QVBoxLayout(analysis_tab)
        at_layout.setContentsMargins(4, 4, 4, 4)

        at_layout.addWidget(QLabel("Vocabulary List (sorted by frequency):"))
        self.vocab_table = QTableWidget(0, 3)
        self.vocab_table.setHorizontalHeaderLabels(["Lemma", "Frequency", "POS"])
        self.vocab_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.vocab_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.vocab_table.setAlternatingRowColors(True)
        at_layout.addWidget(self.vocab_table, stretch=2)

        at_layout.addWidget(QLabel("Grammatical Tense Summary:"))
        self.tense_table = QTableWidget(0, 5)
        self.tense_table.setHorizontalHeaderLabels(
            ["Tense", "Mood", "Person", "Number", "Example"]
        )
        self.tense_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.tense_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tense_table.setAlternatingRowColors(True)
        at_layout.addWidget(self.tense_table, stretch=1)

        self.heatmap_placeholder = QLabel(
            "Word frequency heatmap will appear here after corpus analysis."
        )
        self.heatmap_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.heatmap_placeholder.setStyleSheet(
            "border: 1px dashed #aaa; color: #888; min-height: 120px;"
        )
        at_layout.addWidget(self.heatmap_placeholder, stretch=1)

        self.tab_widget.addTab(analysis_tab, "Corpus Analysis")

        # ── Tab 2: Flashcard Manager (LLR-33) ────────────────────────────────
        self.flashcard_panel = FlashcardManagerPanel()
        self.tab_widget.addTab(self.flashcard_panel, "Flashcards")

        rc_layout.addWidget(self.tab_widget, stretch=1)
        root.addWidget(right_container, stretch=1)

    # ── Public API ────────────────────────────────────────────────────────────

    def add_book(self, title: str, file_path: str) -> None:
        """Register a newly opened book in the library list."""
        self._file_map[title] = file_path
        item = QListWidgetItem(title)
        self.book_list.addItem(item)
        self._set_active_book(title, file_path)

    def populate_vocab(self, rows: list[tuple]) -> None:
        """
        Fill the vocabulary table.
        rows: list of (lemma, frequency, pos) tuples, sorted by frequency desc.
        """
        self.vocab_table.setRowCount(len(rows))
        for r, (lemma, freq, pos) in enumerate(rows):
            self.vocab_table.setItem(r, 0, QTableWidgetItem(lemma))
            self.vocab_table.setItem(r, 1, QTableWidgetItem(str(freq)))
            self.vocab_table.setItem(r, 2, QTableWidgetItem(pos))

    def populate_tenses(self, rows: list[tuple]) -> None:
        """
        Fill the tense summary table.
        rows: list of (tense, mood, person, number, example) tuples.
        """
        self.tense_table.setRowCount(len(rows))
        for r, row_data in enumerate(rows):
            for c, val in enumerate(row_data):
                self.tense_table.setItem(r, c, QTableWidgetItem(str(val)))

    def replace_heatmap(self, canvas_widget: QWidget) -> None:
        """Swap the placeholder label for the actual matplotlib canvas (LLR-18)."""
        layout = self.heatmap_placeholder.parent().layout()
        if layout:
            layout.replaceWidget(self.heatmap_placeholder, canvas_widget)
            self.heatmap_placeholder.hide()
            self.heatmap_placeholder = canvas_widget

    # ── Private helpers ───────────────────────────────────────────────────────

    def _set_active_book(self, title: str, file_path: str) -> None:
        self.book_title_label.setText(title)
        self.analyze_btn.setEnabled(True)
        self.read_btn.setEnabled(True)
        self._active_path = file_path

    def _on_book_double_clicked(self, item: QListWidgetItem) -> None:
        title = item.text()
        path = self._file_map.get(title, "")
        if path:
            self._set_active_book(title, path)
            self.book_selected.emit(path)

    def _on_analyze_clicked(self) -> None:
        if hasattr(self, "_active_path"):
            self.analyze_requested.emit(self._active_path)

    def _on_read_clicked(self) -> None:
        if hasattr(self, "_active_path"):
            self.open_reader_requested.emit(self._active_path)
