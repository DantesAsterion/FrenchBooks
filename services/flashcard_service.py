"""
FlashcardService — cloze-deletion card management and Anki export (HLR-08, HLR-09)

Pure Python domain layer; zero PyQt6 imports (consistent with MVC Model discipline).
Owns FlashcardRecord creation, in-memory storage, CSV export, and audio path generation.
"""

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Domain model ─────────────────────────────────────────────────────────────

@dataclass
class FlashcardRecord:
    """
    Immutable-ish value object representing one cloze-deletion flashcard (LLR-24).

    Fields:
        word:           Surface form of the target word as it appears in the text.
        lemma:          Dictionary form (spaCy token.lemma_).
        sentence:       Full original sentence containing the word.
        cloze_sentence: Sentence with the target word replaced by "_____".
        definition:     User-provided or auto-generated definition (may be empty).
        audio_path:     Absolute path to synthesized MP3, or "" if not yet generated.
        source_file:    Absolute path of the source PDF/EPUB.
        page_index:     Zero-based page/chapter index within the source file.
    """
    word:           str
    lemma:          str
    sentence:       str
    cloze_sentence: str
    definition:     str = ""
    audio_path:     str = ""
    source_file:    str = ""
    page_index:     int = 0


# ── Service ───────────────────────────────────────────────────────────────────

class FlashcardService:
    """
    Manages the in-memory flashcard collection, CSV export, and audio path
    resolution (LLR-26).

    This class is instantiated once by MainWindow after the NLP engine loads
    and shared between ReaderController and DashboardController via MainWindow.
    """

    def __init__(self, audio_dir: str = "flashcards/audio"):
        self._cards: list[FlashcardRecord] = []
        self._audio_dir = Path(audio_dir)
        self._audio_dir.mkdir(parents=True, exist_ok=True)   # LLR-28

    # ── Card management ───────────────────────────────────────────────────────

    def add_card(
        self,
        word: str,
        lemma: str,
        sentence: str,
        cloze_sentence: str,
        source_file: str,
        page_index: int,
        definition: str = "",
    ) -> FlashcardRecord:
        """
        Create and append a FlashcardRecord. Returns the new record so the
        caller can immediately request audio synthesis for it.
        """
        record = FlashcardRecord(
            word=word,
            lemma=lemma,
            sentence=sentence,
            cloze_sentence=cloze_sentence,
            definition=definition,
            source_file=source_file,
            page_index=page_index,
        )
        self._cards.append(record)
        return record

    def add_card_from_token(
        self,
        token,
        doc,
        source_file: str,
        page_index: int,
        definition: str = "",
    ) -> Optional[FlashcardRecord]:
        """
        Convenience wrapper that extracts sentence context directly from a
        spaCy Token (LLR-25, LLR-34).

        Args:
            token:       spaCy Token object for the target word.
            doc:         The spaCy Doc the token belongs to (used for annotation check).
            source_file: Path to the source PDF/EPUB.
            page_index:  Zero-based page/chapter number.
            definition:  Optional definition string.

        Returns:
            The new FlashcardRecord, or None if sentence segmentation is unavailable.
        """
        # LLR-34: guard against missing sentence annotation
        if doc.has_annotation("SENT_START"):
            sentence = token.sent.text.strip()
        else:
            # Fallback: use all text before and after up to 200 chars
            start = max(0, token.idx - 100)
            end   = min(len(doc.text), token.idx + 100)
            sentence = doc.text[start:end].strip()

        cloze = sentence.replace(token.text, "_____", 1)   # LLR-25
        return self.add_card(
            word=token.text,
            lemma=token.lemma_,
            sentence=sentence,
            cloze_sentence=cloze,
            source_file=source_file,
            page_index=page_index,
            definition=definition,
        )

    def get_cards(self) -> list[FlashcardRecord]:
        return list(self._cards)

    def delete_card(self, index: int) -> None:
        if 0 <= index < len(self._cards):
            del self._cards[index]

    def clear(self) -> None:
        self._cards.clear()

    def update_audio_path(self, index: int, path: str) -> None:
        """Called by AudioController once synthesis completes."""
        if 0 <= index < len(self._cards):
            self._cards[index].audio_path = path

    # ── Export ────────────────────────────────────────────────────────────────

    def export_csv(self, output_path: str) -> None:
        """
        Write all cards to a semicolon-delimited, UTF-8 CSV compatible with
        Anki's import dialog (LLR-27).

        Column order: Front; Back; Audio
        """
        with open(output_path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, delimiter=";")
            writer.writerow(["Front", "Back", "Audio"])
            for card in self._cards:
                back  = (f"{card.word} — {card.definition}"
                         if card.definition else card.word)
                audio = (f"[sound:{Path(card.audio_path).name}]"
                         if card.audio_path else "")
                writer.writerow([card.cloze_sentence, back, audio])

    # ── Audio path resolution ─────────────────────────────────────────────────

    def audio_path_for(self, record: FlashcardRecord) -> Path:
        """
        Return the canonical MP3 output path for a record (LLR-28).
        The filename is derived from the lemma + a short hash of the sentence
        to avoid collisions between cards with the same lemma.
        """
        safe_lemma = "".join(
            c if (c.isalnum() or c in "-_") else "_"
            for c in record.lemma[:24]
        )
        short_hash = hashlib.md5(
            record.sentence.encode("utf-8")
        ).hexdigest()[:6]
        return self._audio_dir / f"{safe_lemma}_{short_hash}.mp3"

    @property
    def audio_dir(self) -> Path:
        return self._audio_dir

    def __len__(self) -> int:
        return len(self._cards)
