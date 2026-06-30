# Recreate.md — Environment Reconstruction Guide
## FrenchBooks: Interactive French Literature Study Tool
**OS Target:** Windows 10 (PowerShell 5.1+)
**Last Updated:** 2026-06-30
**Requirement Reference:** LLR-22

---

## Purpose

This document is the authoritative, step-by-step walkthrough for rebuilding the complete
development environment for FrenchBooks from a bare Windows 10 machine. Every PowerShell
command that was ever run during development is recorded here in order of execution.
If you can follow this document top to bottom, you will arrive at a fully working
development environment.

---

## Section 1 — Prerequisites

### 1.1 Required Software (install manually before proceeding)

| Software | Version | Download |
|---|---|---|
| Python | 3.11+ | https://www.python.org/downloads/ |
| Git | 2.40+ | https://git-scm.com/download/win |
| GitHub CLI (`gh`) | 2.40+ | https://cli.github.com/ |
| LaTeX Distribution | TeX Live 2024 or MiKTeX | https://miktex.org/ |

**Python installation note:** During the Python installer, check the box **"Add Python to
PATH"**. Without this, `python` and `pip` will not be found in PowerShell.

### 1.2 Verify Prerequisites

Open PowerShell and verify each tool is available:

```powershell
python --version
# Expected: Python 3.11.x or higher

pip --version
# Expected: pip 23.x from Python 3.11

git --version
# Expected: git version 2.40.x

gh --version
# Expected: gh version 2.40.x
```

---

## Section 2 — Repository Setup

### 2.1 Clone the Repository

```powershell
# Navigate to your desired parent directory
cd C:\Users\<YourUsername>\Documents\repos

# Clone the repository
git clone https://github.com/DantesAsterion/FrenchBooks.git

# Enter the project directory
cd FrenchBooks
```

### 2.2 Verify Branch Structure

```powershell
git branch -a
# Expected branches: master, develop, feature/*, and corresponding remotes
```

---

## Section 3 — Virtual Environment Setup

A Python virtual environment isolates project dependencies from the system Python
installation. All pip installs below must be performed inside the activated venv.

### 3.1 Create the Virtual Environment

```powershell
# Run from the FrenchBooks project root directory
python -m venv venv
```

This creates a `venv/` folder inside the project. It contains a private copy of the
Python interpreter and will hold all installed packages.

### 3.2 Activate the Virtual Environment

```powershell
# This command must be run every time you open a new PowerShell session
.\venv\Scripts\Activate.ps1
```

**Execution Policy Note:** If PowerShell blocks the script with an "execution policy"
error, run the following command once (as Administrator) and then retry activation:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

After successful activation, your prompt will show `(venv)` as a prefix:
```
(venv) PS C:\Users\...\FrenchBooks>
```

### 3.3 Upgrade pip

```powershell
python -m pip install --upgrade pip
```

---

## Section 4 — Python Package Installation

All packages below are installed in the active `venv`. Run these commands in order.

### 4.1 GUI Framework — PyQt6

```powershell
pip install PyQt6
```

PyQt6 is the Python binding for the Qt 6 cross-platform GUI framework. It provides all
widgets, layout managers, event loops, threading primitives, and signal/slot mechanisms
used by this application.

**Version installed during baseline:** PyQt6 >= 6.6

### 4.2 Web Engine (EPUB HTML Rendering) — PyQt6-WebEngine

```powershell
pip install PyQt6-WebEngine
```

PyQt6-WebEngine provides the `QWebEngineView` widget, which embeds a Chromium-based web
engine directly inside a PyQt6 window. It is required for rendering EPUB chapter HTML
content natively in the reader panel.

**Version installed during baseline:** PyQt6-WebEngine >= 6.6

### 4.3 PDF Rendering — PyMuPDF (fitz)

```powershell
pip install PyMuPDF
```

PyMuPDF (imported as `fitz`) is a Python binding for the MuPDF rendering library. It is
used to open PDF files, convert individual pages to pixel data (bitmaps), and extract
plain text from pages for NLP processing.

**Version installed during baseline:** PyMuPDF >= 1.24

### 4.4 EPUB Parsing — EbookLib

```powershell
pip install ebooklib
```

EbookLib is a Python library for reading and writing EPUB 2/3 files. It is used to open
EPUB archives, iterate the document spine (chapter order), and extract the raw HTML
content of each chapter.

**Version installed during baseline:** EbookLib >= 0.18

### 4.5 French NLP Engine — spaCy

```powershell
pip install spacy
```

spaCy is an industrial-strength Natural Language Processing library. For this project it
performs tokenization, lemmatization, Part-of-Speech tagging, dependency parsing, and
morphological analysis on French text.

**Version installed during baseline:** spaCy >= 3.7

### 4.6 Visualization — matplotlib

```powershell
pip install matplotlib
```

matplotlib is the standard Python plotting library. It is used to generate the word
frequency heatmap displayed in the Library Dashboard. The `FigureCanvasQTAgg` backend
renders matplotlib figures as native PyQt6 widgets.

**Version installed during baseline:** matplotlib >= 3.8

### 4.7 Data Handling — pandas (optional, for tense summary tables)

```powershell
pip install pandas
```

pandas provides the `DataFrame` data structure used to organize and display the tense
summary table on the Library Dashboard.

**Version installed during baseline:** pandas >= 2.1

### 4.8 HTML Parsing — BeautifulSoup4 (for EPUB text extraction)

```powershell
pip install beautifulsoup4 lxml
```

BeautifulSoup4 is used to strip HTML tags from EPUB chapter content before passing
plain text to the spaCy NLP pipeline. The `lxml` package provides a fast HTML parser
used as the backend for BeautifulSoup4.

**Version installed during baseline:** beautifulsoup4 >= 4.12, lxml >= 5.0

### 4.9 Install All Packages in One Command (shortcut)

```powershell
pip install PyQt6 PyQt6-WebEngine PyMuPDF ebooklib spacy matplotlib pandas beautifulsoup4 lxml
```

---

## Section 5 — spaCy French Language Model

After installing spaCy, you must separately download the French language model. This
model file (~50 MB) contains the trained neural network weights for French NLP tasks.

### 5.1 Download the French Model

```powershell
python -m spacy download fr_core_news_md
```

`fr_core_news_md` is the medium-sized French model. It includes:
- A French tokenizer
- A statistical POS tagger
- A lemmatizer (trained on the French Sequoia corpus)
- A dependency parser
- Named Entity Recognition (NER)
- Morphological feature analysis (tense, mood, person, number)

### 5.2 Verify the Model Loads

```powershell
python -c "import spacy; nlp = spacy.load('fr_core_news_md'); print(nlp.lang)"
# Expected output: fr
```

---

## Section 6 — Generate requirements.txt

```powershell
pip freeze > requirements.txt
```

The generated `requirements.txt` pins exact package versions and can be used later to
reproduce the exact environment:

```powershell
pip install -r requirements.txt
```

---

## Section 7 — Project Directory Structure

After completing all steps, the project structure should match the following layout:

```
FrenchBooks/
├── venv/                       # Virtual environment (never committed to git)
├── models/                     # MVC Model layer
│   └── document_model.py
├── views/                      # MVC View layer (PyQt6 widgets)
│   ├── main_window.py
│   ├── dashboard_view.py
│   ├── reader_view.py
│   └── study_guide_panel.py
├── controllers/                # MVC Controller layer
│   └── reader_controller.py
├── workers/                    # QRunnable NLP worker threads
│   └── nlp_worker.py
├── assets/                     # Icons, stylesheets
├── Requirements.md             # DO-178C requirements specification
├── Recreate.md                 # This file
├── Documentation.tex           # LaTeX technical book
├── CLAUDE.md                   # AI assistant project guidelines
├── requirements.txt            # Pinned Python dependencies
└── main.py                     # Application entry point
```

---

## Section 8 — Running the Application

```powershell
# Ensure venv is activated (see Section 3.2)
.\venv\Scripts\Activate.ps1

# Launch the application
python main.py
```

---

## Section 9 — Compiling the LaTeX Documentation

```powershell
# From the project root, compile Documentation.tex
pdflatex Documentation.tex
pdflatex Documentation.tex   # Run twice to resolve cross-references
```

The output `Documentation.pdf` will be generated in the project root.

---

## Change Log

| Date | Section Updated | Reason | Commit Ref |
|---|---|---|---|
| 2026-06-30 | All sections created | Initial documentation setup | feature/documentation-setup |

---

*End of Recreate.md — keep this file updated with every environment change.*
