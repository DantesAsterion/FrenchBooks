"""
StudyGuidePanel — MVC View layer (LLR-02, LLR-14, LLR-15, LLR-16)

Displays per-page NLP results. Receives a spaCy Doc from the Controller;
renders lemmas, POS tags, and morphological features.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QListWidget,
    QMenu, QListWidgetItem as _LWI
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QFont


TENSE_COLORS = {
    "Pres": "#d4edda",
    "Imp":  "#fff3cd",
    "Past": "#cce5ff",
    "Fut":  "#f8d7da",
}


class StudyGuidePanel(QWidget):
    """
    Left-panel widget for the split-screen reader.

    Sections:
    1. Verb Table — token, lemma, POS, tense, mood, person, number (LLR-14, LLR-15)
    2. Lemma List — alphabetical list of content-word lemmas (LLR-16)

    Right-click on any row/item emits add_to_flashcard_requested for cloze card
    creation (LLR-32).
    """

    VERB_COLS = ["Token", "Lemma", "POS", "Tense", "Mood", "Person", "Number"]

    # Emitted when user right-clicks and selects "Add to Flashcards" (LLR-32)
    add_to_flashcard_requested = pyqtSignal(
        str,   # word (surface form)
        str,   # lemma
        str,   # sentence (full)
        str,   # cloze_sentence (with _____)
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_doc  = None   # stores the spaCy Doc for context-menu lookups
        self._verb_tokens: list = []  # parallel to verb_table rows (LLR-32)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        title = QLabel("Study Guide")
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        title.setFont(font)
        root.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # ── Verb analysis table ──────────────────────────────────────────────
        verb_container = QWidget()
        vc_layout = QVBoxLayout(verb_container)
        vc_layout.setContentsMargins(0, 0, 0, 0)
        vc_layout.addWidget(QLabel("Verbs & Tenses:"))

        self.verb_table = QTableWidget(0, len(self.VERB_COLS))
        self.verb_table.setHorizontalHeaderLabels(self.VERB_COLS)
        self.verb_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.verb_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.verb_table.setAlternatingRowColors(True)
        self.verb_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.verb_table.customContextMenuRequested.connect(self._verb_context_menu)
        vc_layout.addWidget(self.verb_table)
        splitter.addWidget(verb_container)

        # ── Content-word lemma list ──────────────────────────────────────────
        lemma_container = QWidget()
        lc_layout = QVBoxLayout(lemma_container)
        lc_layout.setContentsMargins(0, 0, 0, 0)
        lc_layout.addWidget(QLabel("Content-Word Lemmas:"))

        self.lemma_list = QListWidget()
        self.lemma_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lemma_list.customContextMenuRequested.connect(self._lemma_context_menu)
        lc_layout.addWidget(self.lemma_list)
        splitter.addWidget(lemma_container)

        splitter.setSizes([300, 200])
        root.addWidget(splitter)

    # ── Public API called by the Controller ──────────────────────────────────

    def update_from_doc(self, doc) -> None:
        """
        Populate the panel from a spaCy Doc object (LLR-14, LLR-15, LLR-16).
        Also stores the doc reference for right-click flashcard creation (LLR-32).
        This slot runs on the main GUI thread (delivered via Qt signal).
        """
        self._current_doc = doc
        self._populate_verb_table(doc)
        self._populate_lemma_list(doc)

    def clear(self) -> None:
        self._current_doc = None
        self._verb_tokens.clear()
        self.verb_table.setRowCount(0)
        self.lemma_list.clear()

    # ── Private helpers ──────────────────────────────────────────────────────

    def _populate_verb_table(self, doc) -> None:
        """Build the verb/tense table from the spaCy Doc (LLR-14, LLR-15)."""
        verbs = [t for t in doc if t.pos_ in ("VERB", "AUX") and not t.is_punct]
        self._verb_tokens = verbs   # parallel list for context-menu lookup (LLR-32)
        self.verb_table.setRowCount(len(verbs))

        for row, token in enumerate(verbs):
            morph = token.morph.to_dict()
            tense  = morph.get("Tense",  "—")
            mood   = morph.get("Mood",   "—")
            person = morph.get("Person", "—")
            number = morph.get("Number", "—")

            values = [token.text, token.lemma_, token.pos_,
                      tense, mood, person, number]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 3 and tense in TENSE_COLORS:
                    item.setBackground(QColor(TENSE_COLORS[tense]))
                self.verb_table.setItem(row, col, item)

    def _populate_lemma_list(self, doc) -> None:
        """List unique content-word lemmas in alphabetical order (LLR-16)."""
        self.lemma_list.clear()
        seen = set()
        lemmas = []
        for token in doc:
            if token.is_stop or token.is_punct or token.is_space:
                continue
            lemma = token.lemma_.lower()
            if lemma not in seen:
                seen.add(lemma)
                lemmas.append(lemma)
        for lemma in sorted(lemmas):
            self.lemma_list.addItem(lemma)

    # ── Right-click context menus (LLR-32) ────────────────────────────────────

    def _verb_context_menu(self, pos: QPoint) -> None:
        """Context menu for the verb table rows."""
        row = self.verb_table.rowAt(pos.y())
        if row < 0 or row >= len(self._verb_tokens):
            return
        token = self._verb_tokens[row]
        menu = QMenu(self)
        action = menu.addAction(f"Add '{token.text}' to Flashcards")
        if menu.exec(self.verb_table.viewport().mapToGlobal(pos)) == action:
            self._emit_flashcard_signal(token)

    def _lemma_context_menu(self, pos: QPoint) -> None:
        """Context menu for the lemma list items."""
        item = self.lemma_list.itemAt(pos)
        if item is None or self._current_doc is None:
            return
        lemma_text = item.text()
        # Find first non-stop token whose lemma matches the selected lemma
        token = next(
            (t for t in self._current_doc
             if t.lemma_.lower() == lemma_text
             and not t.is_stop and not t.is_punct),
            None
        )
        if token is None:
            return
        menu = QMenu(self)
        action = menu.addAction(f"Add '{token.text}' to Flashcards")
        if menu.exec(self.lemma_list.viewport().mapToGlobal(pos)) == action:
            self._emit_flashcard_signal(token)

    def _emit_flashcard_signal(self, token) -> None:
        """
        Extract sentence from the token and emit add_to_flashcard_requested (LLR-25, LLR-34).
        """
        doc = self._current_doc
        if doc is None:
            return
        if doc.has_annotation("SENT_START"):
            sentence = token.sent.text.strip()
        else:
            # Fallback: 200-char window around the token (LLR-34)
            start = max(0, token.idx - 100)
            end   = min(len(doc.text), token.idx + 100)
            sentence = doc.text[start:end].strip()

        cloze = sentence.replace(token.text, "_____", 1)
        self.add_to_flashcard_requested.emit(
            token.text, token.lemma_, sentence, cloze
        )
