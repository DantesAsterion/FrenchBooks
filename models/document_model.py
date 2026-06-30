"""
DocumentModel — MVC Model layer (LLR-01)

Encapsulates all state for a loaded document. No PyQt6 imports allowed here.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional


class DocumentType(Enum):
    PDF  = auto()
    EPUB = auto()


@dataclass
class PageCache:
    """Stores raw text and NLP result for a single page/chapter."""
    raw_text:    Optional[str] = None
    nlp_doc:     Optional[object] = None   # spaCy Doc, typed as object to avoid import


@dataclass
class DocumentModel:
    """
    Holds all data for one loaded book.

    Attributes:
        file_path:   Absolute path to the PDF or EPUB file.
        doc_type:    PDF or EPUB.
        page_count:  Total number of pages (PDF) or chapters (EPUB).
        title:       Book title extracted from metadata, or filename.
        page_cache:  Dict mapping page index -> PageCache.
        corpus_nlp:  Cached full-document spaCy Doc (set after dashboard analysis).
    """
    file_path:   str               = ""
    doc_type:    Optional[DocumentType] = None
    page_count:  int               = 0
    title:       str               = "Untitled"
    page_cache:  dict              = field(default_factory=dict)
    corpus_nlp:  Optional[object]  = None

    def get_page_cache(self, index: int) -> PageCache:
        """Return (creating if absent) the cache entry for a page index."""
        if index not in self.page_cache:
            self.page_cache[index] = PageCache()
        return self.page_cache[index]

    def set_page_text(self, index: int, text: str) -> None:
        self.get_page_cache(index).raw_text = text

    def get_page_text(self, index: int) -> Optional[str]:
        return self.page_cache.get(index, PageCache()).raw_text

    def set_page_nlp(self, index: int, doc: object) -> None:
        self.get_page_cache(index).nlp_doc = doc

    def get_page_nlp(self, index: int) -> Optional[object]:
        return self.page_cache.get(index, PageCache()).nlp_doc

    def is_cached(self, index: int) -> bool:
        """Return True if NLP results for this page are already computed."""
        return self.page_cache.get(index, PageCache()).nlp_doc is not None
