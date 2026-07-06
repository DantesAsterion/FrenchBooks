# Requirements.md — French Interactive Reader
## DO-178C Software Requirements Specification
**Project:** FrenchBooks — Interactive French Literature Study Tool
**Version:** 1.1.0
**Date:** 2026-07-05
**Author:** AsterionDantes
**Status:** CHANGE BASELINE — Cloze Flashcard Engine Amendment

---

## 1. Document Purpose

This document establishes the complete software requirements baseline for the FrenchBooks
desktop application. It is governed by DO-178C (Software Considerations in Airborne Systems
and Equipment Certification) principles adapted for desktop application development. All
High-Level Requirements (HLR) and Low-Level Requirements (LLR) defined herein are the
authoritative source for design, implementation, and verification activities. **No code may
be written without a traceable requirement.**

---

## 2. System Overview

FrenchBooks is a Python/PyQt6 desktop application that:
- Loads and renders `.pdf` and `.epub` documents natively within its own GUI
- Provides a library dashboard with corpus-wide NLP analysis (word heatmap, tense summary,
  vocabulary list)
- Provides a split-screen reader where the right panel shows the live document and the left
  panel shows a dynamically-updating NLP study guide for the current page
- Executes all heavy NLP work off the main GUI thread using Qt threading primitives
- Generates context-aware, cloze-deletion flashcards from source sentences and exports
  them as Anki-compatible CSV with synthesized French audio (v1.1.0 amendment)

**Target Platform:** Windows 10 (PowerShell environment)
**Core Language:** Python 3.x
**GUI Toolkit:** PyQt6
**NLP Engine:** spaCy `fr_core_news_md`

---

## 3. High-Level Requirements (HLR)

### HLR-01 — Library Dashboard
The system shall provide a Library Dashboard view that displays all loaded books, and for
each book shall be capable of generating:
- (a) A word frequency heatmap across the entire document
- (b) A summary of all grammatical tenses (tense, mood, number, person) present in the book
- (c) A deduplicated, frequency-sorted vocabulary list of content words

**Priority:** High
**Rationale:** Core feature enabling corpus-level study.

---

### HLR-02 — Native Document Rendering
The system shall natively render `.pdf` and `.epub` documents within its own GUI window.
No external viewer or browser process shall be launched to display document content.

**Priority:** Critical
**Rationale:** The application is a self-contained reader; external dependencies would
violate user experience and auditability requirements.

---

### HLR-03 — Dynamic NLP Study Guide Panel
The system shall provide a Study Guide panel that updates automatically whenever the user
navigates to a new page. The panel shall perform per-page NLP analysis and display:
- (a) All unique lemmas visible on the current page
- (b) All verbs isolated by Part-of-Speech (POS) tag
- (c) Grammatical tense/mood/aspect of each verb (via morphological analysis)
- (d) Definitions or usage notes for selected vocabulary items

**Priority:** Critical
**Rationale:** Core differentiating feature of the application.

---

### HLR-04 — GUI Thread Safety and Responsiveness
The application's main GUI thread shall remain responsive at all times. All NLP processing,
file parsing, and document analysis operations that may take longer than 100 ms shall be
dispatched to a background thread.

**Priority:** Critical
**Rationale:** A frozen GUI violates basic usability; in DO-178C terms this is a safety
requirement for user-perceived system integrity.

---

### HLR-05 — Model-View-Controller Architecture
The system's software architecture shall conform to the Model-View-Controller (MVC) pattern:
- **Model:** Data structures and domain logic (file parsing, NLP results, book metadata)
- **View:** PyQt6 widgets responsible only for rendering data
- **Controller:** Mediators between View events and Model operations

No View component shall contain data-parsing or NLP logic. No Model component shall import
or reference PyQt6 widgets.

**Priority:** High
**Rationale:** Separation of concerns enables independent verification of each layer.

---

### HLR-06 — French NLP Engine
The system shall use spaCy version ≥ 3.0 with the `fr_core_news_md` French language model
for all natural language processing operations, including but not limited to: tokenization,
lemmatization, POS tagging, dependency parsing, and morphological feature extraction.

**Priority:** High
**Rationale:** `fr_core_news_md` provides the necessary French morphological data required
for accurate tense and mood identification.

---

### HLR-07 — Documentation and Traceability Pipeline
Every software change shall be:
- (a) Committed with a message that references a specific HLR or LLR identifier
- (b) Reflected by an update to `Recreate.md` for any environment change
- (c) Reflected by an update to `Documentation.tex` for any new module or library

**Priority:** High
**Rationale:** Traceability is a fundamental DO-178C obligation. No change is considered
complete until documentation is updated.

---

### HLR-08 — Contextual (Cloze-Deletion) Flashcard Engine
The system shall generate cloze-deletion flashcards from source document text. Each card
shall present the **complete sentence** in which a target word appears (extracted via the
spaCy `token.sent` span), with the target word replaced by a blank, as the card "Front".
The word's lemma and user-provided or auto-generated definition shall form the card "Back".
Users shall be able to create cards from any token in the Study Guide panel via a
right-click context menu.

**Priority:** High
**Rationale:** Cognitive science research (Wittrock, 1992; Nation, 2001) establishes that
sentence-context (cloze-format) exposure produces significantly stronger vocabulary
retention than isolated word-translation pairs.

---

### HLR-09 — Anki Export Compatibility
The system shall export the in-memory flashcard collection as a UTF-8 encoded,
semicolon-delimited CSV file directly importable into Anki. Each row shall contain the
cloze sentence (Front), the word and definition (Back), and an Anki audio media tag
(`[sound:<file.mp3>]`) in the Audio column. The exported CSV shall require no manual
reformatting before Anki import.

**Priority:** High
**Rationale:** Anki is the dominant spaced-repetition platform. Direct compatibility
eliminates the friction of manual card creation.

---

### HLR-10 — French Text-to-Speech Audio Synthesis
The system shall synthesize native-sounding French audio for flashcard sentences using
`gTTS` (Google Text-to-Speech) as the primary engine. Each synthesized file shall be
saved as an MP3 in a designated output directory. Audio synthesis shall be dispatched in
a background thread consistent with HLR-04. The Dashboard Flashcard Manager panel shall
provide audio preview controls (Play, Pause, Stop, Speed).

**Priority:** Medium
**Rationale:** Audio reinforcement of sentence-context cards accelerates phonological
acquisition and is required for Anki audio-card format.

---

## 4. Low-Level Requirements (LLR)

### 4.1 Architecture (derived from HLR-05)

**LLR-01**
A `DocumentModel` class shall be defined in `models/document_model.py`. It shall encapsulate
all state related to a loaded document: file path, file type (PDF/EPUB), page count, raw
page text cache, and NLP result cache. It shall expose no PyQt6 types.
*Parent: HLR-05*

**LLR-02**
All PyQt6 widget classes (main window, dashboard view, reader view, study guide panel) shall
be defined under a `views/` directory. They shall receive pre-processed data objects from
the Controller and render them. They shall not call `spacy.load()` or `fitz.open()`.
*Parent: HLR-05*

**LLR-03**
A `ReaderController` class shall be defined in `controllers/reader_controller.py`. It shall:
- Respond to page-navigation signals emitted by the View
- Retrieve raw page text from the DocumentModel
- Dispatch NLP worker threads when new page text is available
- Receive worker results via Qt signals and forward them to the Study Guide View
*Parent: HLR-05*

---

### 4.2 PDF Rendering (derived from HLR-02)

**LLR-04**
PDF documents shall be opened using `fitz.open()` (PyMuPDF). Each page shall be rendered by
calling `page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))`, where `zoom` is a configurable
DPI scaling factor (default: 1.5, equating to approximately 108 DPI).
*Parent: HLR-02*

**LLR-05**
The raw pixel data from `fitz.Pixmap` shall be converted to a `QPixmap` by constructing a
`QImage` from the pixmap's `samples` bytes, `width`, `height`, and `stride` properties with
format `QImage.Format.Format_RGB888`. The `QImage` shall then be converted to `QPixmap` via
`QPixmap.fromImage()`.
*Parent: HLR-02, LLR-04*

**LLR-06**
The PDF page `QPixmap` shall be displayed in a `QLabel` embedded within a `QScrollArea` to
allow panning of large pages without clipping.
*Parent: HLR-02, LLR-05*

---

### 4.3 EPUB Rendering (derived from HLR-02)

**LLR-07**
EPUB documents shall be opened using `ebooklib.epub.read_epub()`. The spine items (ordered
chapter list) shall be iterated to establish a logical page/chapter ordering.
*Parent: HLR-02*

**LLR-08**
Each EPUB chapter's HTML content shall be extracted from the `EpubHtml` item's `get_content()`
method, decoded as UTF-8, and rendered in a `QWebEngineView` widget using `setHtml()`.
*Parent: HLR-02, LLR-07*

**LLR-09**
If `QWebEngineView` is unavailable, the system shall fall back to `QTextBrowser` which renders
a subset of HTML. The fall-back shall be documented in `Documentation.tex`.
*Parent: HLR-02, LLR-08*

---

### 4.4 Threading Architecture (derived from HLR-04)

**LLR-10**
An `NLPWorker` class shall subclass `QRunnable`. It shall accept raw page text as input and
shall call `nlp(text)` (the spaCy pipeline) within its `run()` method.
*Parent: HLR-04*

**LLR-11**
The `NLPWorker` shall emit results via a `WorkerSignals` helper object (subclassing
`QObject`) using a `finished` signal typed `pyqtSignal(object)`. Direct return values from
`QRunnable.run()` are not accessible from outside the thread.
*Parent: HLR-04, LLR-10*

**LLR-12**
Workers shall be dispatched via `QThreadPool.globalInstance().start(worker)`. The thread pool
manages worker lifecycle; the Controller shall not manually manage thread objects.
*Parent: HLR-04, LLR-10*

**LLR-13**
If the user navigates pages faster than the NLP worker completes, the pending worker for the
previous page shall be cancelled (via a thread-safe cancellation flag) before the new worker
is dispatched.
*Parent: HLR-04*

---

### 4.5 Study Guide Panel (derived from HLR-03)

**LLR-14**
The study guide panel shall display a `QTableWidget` with columns: Token, Lemma, POS, Tense,
Mood, Person, Number. One row per unique token found on the current page.
*Parent: HLR-03*

**LLR-15**
The tense/mood identification algorithm shall read the `morph` attribute of each spaCy `Token`
object. Specifically, it shall extract the `Tense`, `Mood`, `Person`, and `Number` keys from
the `token.morph.to_dict()` result for tokens where `token.pos_ == "VERB"`.
*Parent: HLR-03, HLR-06, LLR-14*

**LLR-16**
The study guide panel shall display a separate section listing all unique lemmas (content words
only, filtering `token.is_stop == True`) in alphabetical order.
*Parent: HLR-03*

---

### 4.6 Library Dashboard NLP (derived from HLR-01)

**LLR-17**
The global word heatmap shall be generated by `matplotlib` (`pyplot.imshow()` or equivalent).
Word frequency counts shall be computed using `collections.Counter` over all lemmatized,
non-stop-word tokens across the entire document. The top N words shall be visualized.
*Parent: HLR-01*

**LLR-18**
The heatmap figure shall be embedded in the PyQt6 Dashboard view using
`matplotlib.backends.backend_qtagg.FigureCanvasQTAgg` to avoid spawning a separate
matplotlib window.
*Parent: HLR-01, LLR-17*

**LLR-19**
The tense summary for the dashboard shall be a `pandas.DataFrame` (or `dict`) of
`{(Tense, Mood, Person, Number): [example_sentences]}` keyed by morphological feature
combinations, generated once upon document load and cached in `DocumentModel`.
*Parent: HLR-01, HLR-06, LLR-01*

**LLR-20**
The vocabulary list shall exclude French stop words (as identified by `token.is_stop`) and
punctuation (`token.is_punct`), and shall be sorted descending by frequency count.
*Parent: HLR-01, LLR-01*

---

### 4.7 Documentation Traceability (derived from HLR-07)

**LLR-21**
Every git commit message shall conform to the format:
```
<type>(<scope>): <imperative description> [<HLR-XX|LLR-XX>]
```
Permitted types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
Example: `feat(reader): render PDF page as QPixmap [LLR-05]`
*Parent: HLR-07*

**LLR-22**
`Recreate.md` shall be updated in the same commit as any change that introduces a new
`pip install`, PowerShell command, or environment configuration step.
*Parent: HLR-07*

**LLR-23**
`Documentation.tex` shall contain at minimum one chapter per feature branch merged into
`develop`. Each chapter shall explain the concepts, libraries, and design decisions in plain
English accessible to a non-programmer.
*Parent: HLR-07*

---

### 4.8 Cloze-Deletion Flashcard Engine (derived from HLR-08)

**LLR-24**
A `FlashcardRecord` dataclass shall be defined in `services/flashcard_service.py` with
the following fields: `word` (str), `lemma` (str), `sentence` (str — full original
sentence text), `cloze_sentence` (str — sentence with the target word replaced by
`"_____"`), `definition` (str, may be empty), `audio_path` (str — absolute MP3 path or
empty string), `source_file` (str), `page_index` (int).
*Parent: HLR-08*

**LLR-25**
The cloze sentence shall be constructed by:
1. Accessing `token.sent.text` (the spaCy `Span` enclosing sentence).
2. Replacing the first occurrence of `token.text` with `"_____"` using Python's
   `str.replace(token.text, "_____", 1)`.
Before accessing `token.sent`, the code shall verify `doc.has_annotation("SENT_START")`
to confirm the `fr_core_news_md` parser has segmented sentences (LLR-34).
*Parent: HLR-08, HLR-06*

**LLR-26**
A `FlashcardService` class in `services/flashcard_service.py` shall provide:
- `add_card(word, lemma, sentence, cloze_sentence, source_file, page_index, definition="")`
  → appends a `FlashcardRecord` and returns it
- `get_cards()` → returns a copy of the internal list
- `delete_card(index: int)` → removes by position
- `clear()` → removes all cards
- `export_csv(path: str)` → writes Anki-compatible CSV (see LLR-27)
- `audio_path_for(record)` → returns the canonical MP3 path under the audio directory
*Parent: HLR-08*

**LLR-27**
`FlashcardService.export_csv()` shall produce a semicolon-delimited, UTF-8 encoded CSV
with header `Front;Back;Audio`. Column mapping:
- `Front` = `record.cloze_sentence`
- `Back` = `"{record.word} — {record.definition}"` (or just `record.word` if no definition)
- `Audio` = `[sound:{Path(record.audio_path).name}]` if `record.audio_path` is set, else `""`
*Parent: HLR-09*

**LLR-28**
The `FlashcardService` audio output directory shall default to `flashcards/audio/` under
the project root. The directory shall be created on first use via
`pathlib.Path.mkdir(parents=True, exist_ok=True)`. The path shall be configurable.
*Parent: HLR-10, LLR-26*

---

### 4.9 Audio Synthesis and Playback (derived from HLR-10, HLR-04)

**LLR-29**
An `AudioWorker` class shall subclass `QRunnable`. Constructor arguments: `text` (str),
`output_path` (str), `lang` (str, default `"fr"`). The `run()` method shall call
`gTTS(text=text, lang=lang, slow=False).save(output_path)` inside a `try/except`
block. Results shall be delivered via an `AudioSignals(QObject)` helper with:
- `finished = pyqtSignal(str, str)` — `(text, output_path)` on success
- `error = pyqtSignal(str, str)` — `(text, error_message)` on failure
*Parent: HLR-04, HLR-10*

**LLR-30**
If `gTTS` raises any exception (e.g. network unavailable), the `AudioWorker` shall catch
it, emit `error(text, str(exc))`, and leave `record.audio_path` unchanged (empty). The
flashcard record shall remain valid and exportable; the Anki `Audio` column shall be
empty for that card. This degraded-mode behaviour shall be documented in `Recreate.md`.
*Parent: HLR-10, LLR-33 (forward reference)*

**LLR-31**
An `AudioController` class in `controllers/audio_controller.py` shall:
- Dispatch `AudioWorker` instances via `QThreadPool.globalInstance().start()`
- Maintain a dict `{sentence_hash: worker}` to avoid duplicate synthesis for the same text
- Expose `synthesize(text, output_path)` → dispatches worker
- Expose `play(path)`, `pause()`, `stop()`, `set_playback_rate(rate: float)` using
  `QMediaPlayer` + `QAudioOutput`
- Emit `synthesis_done(text, path)`, `synthesis_error(text, msg)`, `status_message(str)`
*Parent: HLR-04, HLR-10*

**LLR-32**
The `StudyGuidePanel` shall store the most recently delivered spaCy Doc in
`self._current_doc`. When the user right-clicks a row in the verb table or an item in the
lemma list, a `QMenu` shall appear with "Add to Flashcards". Selecting this option shall
emit `add_to_flashcard_requested(word: str, lemma: str, sentence: str, cloze: str)`,
extracting the sentence via `token.sent.text` from the stored Doc.
*Parent: HLR-08, HLR-03*

**LLR-33**
A `FlashcardManagerPanel` widget in `views/flashcard_manager.py` shall be added to the
Dashboard as a new tab in a `QTabWidget`. It shall display all generated cards in a
`QTableWidget` with columns: `Cloze Sentence`, `Word`, `Lemma`, `Audio`. Buttons shall
include: `Synthesize Audio`, `Export CSV…`, `Delete Selected`. Audio preview controls
(Play, Pause, Stop, Speed dropdown) shall be present in a separate control bar.
*Parent: HLR-08, HLR-09, HLR-10*

**LLR-34**
Before calling `token.sent`, the system shall verify `doc.has_annotation("SENT_START")`.
If this returns `False`, the system shall fall back to using the full page/chapter text
as the sentence (i.e. `cloze_sentence = page_text.replace(token.text, "_____", 1)`).
*Parent: HLR-06, HLR-08*

**LLR-35**
`gTTS` shall be listed as a required dependency in `Recreate.md` and installed via
`pip install gTTS`. The `edge-tts` library shall be documented as an optional
higher-quality alternative requiring `pip install edge-tts`, with its async invocation
pattern explained in `Documentation.tex`.
*Parent: HLR-10*

---

## 5. GitFlow Workflow Definition

### 5.1 Branch Taxonomy

| Branch Pattern | Purpose | Lifetime |
|---|---|---|
| `master` | Production-only, release-tagged code | Permanent |
| `develop` | Integration target for completed features | Permanent |
| `feature/<name>` | Single-feature development | Until merged to develop |
| `release/<version>` | Release preparation and hotfix staging | Until merged to master+develop |
| `hotfix/<name>` | Emergency patches from master | Until merged to master+develop |

### 5.2 Branch Rules

1. **No direct commits to `master` after the initial baseline commit.** All changes reach
   `master` only via `release/*` branches.
2. **No direct commits to `develop`** except merge commits from `feature/*` or `release/*`.
3. **Feature branches** are created from `develop`, named `feature/<short-descriptor>`.
4. **Release branches** are created from `develop` when all features for a version are merged.
   Version tags (`v1.0.0`) are applied on `master` after merge.
5. **Hotfix branches** are created from `master` and are merged back to both `master` and
   `develop`.

### 5.3 Merge Protocol

```
feature/* → develop       (via PR; requires review)
develop   → release/*     (manual; begins release cycle)
release/* → master        (merge + tag vX.Y.Z)
release/* → develop       (back-merge to sync)
hotfix/*  → master        (merge + tag vX.Y.Z-p1)
hotfix/*  → develop       (back-merge)
```

### 5.4 Commit Format (see LLR-21)

```
<type>(<scope>): <description> [<REQ-ID>]
```

---

## 6. Traceability Matrix

The following table shall be updated with every commit. It forms the living audit trail
required by DO-178C Section 11 (Software Configuration Management).

| Commit SHA (short) | Type | Scope | Description | Req. ID | Branch |
|---|---|---|---|---|---|
| e3bda6e | docs | baseline | Establish DO-178C requirements baseline and project scaffold | HLR-01..07 | master |
| caf0b66 | docs | setup | Add Recreate.md and Documentation.tex scaffold | HLR-07, LLR-22, LLR-23 | feature/documentation-setup |
| bd1b2c9 | docs | setup | Merge documentation scaffold into develop | HLR-07, LLR-22, LLR-23 | develop |
| f020bdc | feat | gui | MVC skeleton, split-screen layout, threading worker | HLR-04, HLR-05, LLR-01..03, LLR-10..16 | feature/gui-architecture |
| 6f018d4 | docs | trace | Update traceability matrix (first pass) | HLR-07, LLR-21 | feature/gui-architecture |
| 371e074 | feat | gui | Merge GUI architecture into develop | HLR-04, HLR-05 | develop |
| afe0db8 | feat | reader | Native PDF and EPUB renderers implementation | HLR-02, LLR-04..09 | feature/native-readers |
| 6f79c84 | feat | reader | Merge native-readers into develop | HLR-02 | develop |
| a331a48 | feat | nlp | Corpus worker, heatmap canvas, dashboard controller | HLR-01, LLR-17..20 | feature/dynamic-nlp |
| 93cd83f | feat | nlp | Merge dynamic-nlp into develop | HLR-01 | develop |

---

## 7. Verification and Validation

| LLR ID | Verification Method | Pass Criterion |
|---|---|---|
| LLR-04/05/06 | Manual test — open sample PDF, observe rendered page | Page renders without distortion at zoom 1.5 |
| LLR-08 | Manual test — open sample EPUB, observe chapter HTML | Chapter text renders correctly in QWebEngineView |
| LLR-10/11/12 | Code inspection + manual test | GUI remains responsive during NLP processing |
| LLR-14/15 | Manual test — navigate to page with known verbs | Table shows correct tense/mood for each verb |
| LLR-17/18 | Manual test — open dashboard for a loaded book | Heatmap visible within the Qt window, no external window |
| LLR-25 | Manual test — right-click verb in study guide, add card | Card appears with correct cloze blank and source sentence |
| LLR-27 | Manual test — export CSV, import into Anki test deck | Anki imports without error; Front/Back/Audio columns correct |
| LLR-29/30 | Manual test — synthesize audio with network disconnected | AudioWorker emits error signal; card Audio column remains empty |
| LLR-31 | Code inspection + manual test | AudioController plays MP3 without blocking GUI |
| LLR-33 | Manual test — open Flashcard Manager tab | Table shows all cards; Export and Delete buttons functional |

---

*End of Requirements.md v1.1.0 — CHANGE BASELINE (Cloze Flashcard Engine)*
