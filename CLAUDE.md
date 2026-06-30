# Project Guidelines: French Interactive Reader (DO-178C Standard)

## System Environment
- **OS Base:** Windows 10 (PowerShell)
- **Core Stack:** Python 3.x, PyQt6, PyQt6-WebEngine, PyMuPDF (fitz), EbookLib, spaCy (fr_core_news_md), matplotlib, LaTeX.

## Strict DO-178C & GitFlow Architecture
- **Traceability:** ALL git commits must reference a High-Level Requirement (HLR) or Low-Level Requirement (LLR) defined in `Requirements.md`.
- **Commit Format:** `<type>: <description> <HLR/LLR-ID>` (e.g., `feat: setup QWebEngineView for EPUB LLR-05`). Use the `gh` CLI.
- **GitFlow:** Strict adherence to `master`, `develop`, `feature/*`, `release/*`, and `hotfix/*` branch structures. No direct commits to `master` after initialization.

## Architecture & GUI Rules
- **Threading:** NEVER run NLP tasks (spaCy) on the main GUI thread. Always use `QThread` and `QRunnable` (Worker patterns) to keep the PyQt6 UI responsive while analyzing pages.
- **Design Pattern:** Follow Model-View-Controller (MVC) to separate GUI rendering from file parsing and NLP processing.

## Mandatory Documentation Loop
Before concluding any task or generating a git commit, you MUST:
1. **Update `Recreate.md`:** Log any new PowerShell terminal commands, `pip` installs, `spacy` model downloads, or environment changes.
2. **Update `Documentation.tex`:** Explain the underlying theory (PyQt6 native rendering, Threading, French NLP morphology) and document new libraries/functions in plain English for non-programmers.

## Token Optimization Rule
Do not attempt to read or parse `.pdf` or `.epub` files directly. Rely on Python scripts (`PyMuPDF`, `EbookLib`) to extract data from the binary files. Do not index the `venv` folder.