"""
CorpusWorker — full-document NLP analysis (HLR-01, LLR-17, LLR-19, LLR-20)

Processes all pages/chapters of a document in a background QRunnable,
building word frequency counts, tense summaries, and a vocabulary list.
Results arrive on the main thread via Qt signals.
"""

from collections import Counter, defaultdict
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal
import threading


class CorpusSignals(QObject):
    finished = pyqtSignal(object)   # carries a CorpusResult dataclass
    progress = pyqtSignal(int, int) # (pages_done, total_pages)
    error    = pyqtSignal(str)


class CorpusResult:
    """
    Container for all corpus-level NLP analysis outputs.

    Attributes:
        vocab:       list of (lemma, count, pos) sorted by count desc (LLR-20)
        tense_rows:  list of (tense, mood, person, number, example) (LLR-19)
        word_counts: Counter of lemma -> count (for heatmap, LLR-17)
    """

    def __init__(self):
        self.vocab:       list  = []
        self.tense_rows:  list  = []
        self.word_counts: Counter = Counter()


class CorpusWorker(QRunnable):
    """
    Runs spaCy over every page/chapter text in a DocumentModel.

    Args:
        nlp:         The spaCy Language pipeline.
        page_texts:  Ordered list of plain-text strings (one per page/chapter).
    """

    def __init__(self, nlp, page_texts: list[str]):
        super().__init__()
        self.nlp        = nlp
        self.page_texts = page_texts
        self.signals    = CorpusSignals()
        self._cancel    = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        total     = len(self.page_texts)
        lemma_pos : dict[str, str]     = {}          # lemma -> most-common POS
        freq      : Counter            = Counter()
        tense_map : dict               = defaultdict(list)   # (T,M,Pe,N) -> [example]

        for idx, text in enumerate(self.page_texts):
            if self._cancel.is_set():
                return
            if not text.strip():
                self.signals.progress.emit(idx + 1, total)
                continue

            doc = self.nlp(text)

            for token in doc:
                if token.is_stop or token.is_punct or token.is_space:
                    continue
                lemma = token.lemma_.lower()
                freq[lemma] += 1
                lemma_pos.setdefault(lemma, token.pos_)

                if token.pos_ in ("VERB", "AUX"):
                    morph   = token.morph.to_dict()
                    tense   = morph.get("Tense",  "N/A")
                    mood    = morph.get("Mood",   "N/A")
                    person  = morph.get("Person", "N/A")
                    number  = morph.get("Number", "N/A")
                    key     = (tense, mood, person, number)
                    if len(tense_map[key]) < 2:
                        # Store a short example sentence (the sentence containing this token)
                        example = token.sent.text[:80] if token.sent else token.text
                        tense_map[key].append(example)

            self.signals.progress.emit(idx + 1, total)

        if self._cancel.is_set():
            return

        result = CorpusResult()

        # Vocabulary list: top 500, sorted by frequency (LLR-20)
        result.vocab = [
            (lemma, count, lemma_pos.get(lemma, "?"))
            for lemma, count in freq.most_common(500)
        ]
        result.word_counts = freq

        # Tense summary rows (LLR-19)
        for (tense, mood, person, number), examples in sorted(tense_map.items()):
            result.tense_rows.append(
                (tense, mood, person, number, examples[0] if examples else "")
            )

        self.signals.finished.emit(result)
