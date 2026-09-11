# PDF Study Kit

Turn a PDF into an outline, summary, glossary, flashcards, or a practice quiz — **entirely offline**. No API key, no model download, no network call.

```bash
pip install -r requirements.txt
python3 -m pdf_study_kit --pdf lecture.pdf --format flashcards
```

## Why offline, and why extractive

This project was built after looking at [Local-NotebookLM](https://github.com/Goekdeniz-Guelmez/Local-NotebookLM), which turns PDFs into podcasts using local LLMs and TTS. That architecture — installable package, CLI, HTTP API, Docker — is worth copying. The dependency on a model server is not, for a study tool: it puts a GPU and an API key between a student and their lecture notes.

So the analysis is **classical, not generative**:

| Job an LLM would do | What this does instead |
|---|---|
| Identify key concepts | TF-IDF over the document's own sections, unigrams + bigrams |
| Write a summary | Extractive sentence scoring — picks real sentences, never writes new ones |
| Define terms | Definition-pattern matching (`X is defined as…`, `X refers to…`) |
| Write quiz questions | Cloze deletion over key terms, distractors drawn from other key terms |

Extractive summarisation has a property that matters for studying: **every sentence in the output appears verbatim in the source.** A generated summary can hallucinate a fact you then revise from. This one cannot — and there is a test asserting it.

## Formats

| Format | Output |
|---|---|
| `outline` | Section headings with two key sentences each |
| `summary` | Top-ranked sentences plus key terms |
| `glossary` | Defined terms, or highest-TF-IDF terms with context |
| `flashcards` | Q/A cards — definitions and cloze deletions |
| `quiz` | Multiple choice with an answer key |
| `all` | Everything (default) |

## Interfaces

**CLI**
```bash
python3 -m pdf_study_kit --pdf paper.pdf --format quiz --out quiz.md
python3 -m pdf_study_kit --pdf paper.pdf --format summary --sentences 12
```

**Python**
```python
from pdf_study_kit import extract, build
doc = extract("lecture.pdf")
print(build(doc, "flashcards"))
```

**HTTP API**
```bash
python3 -m pdf_study_kit.server          # http://localhost:8000/docs
curl -X POST "http://localhost:8000/generate?format=summary" -F "file=@paper.pdf"
```

**Docker**
```bash
docker build -t pdf-study-kit .
docker run -p 8000:8000 pdf-study-kit
```

## Sample output

Run against `examples/database_normalization.pdf` (a 415-word lecture handout), full output in [`examples/study_kit_output.md`](examples/study_kit_output.md):

**Summary** picks real sentences:
> - First normal form requires that every attribute contain only atomic values, so a column may not hold a list.
> - Boyce-Codd normal form is a stricter version of third normal form in which every determinant must be a candidate key.

**Glossary** extracts definitions:
> **functional dependency** — constraint between two sets of attributes in a relation
> **deletion anomaly** — loss of one fact as a side effect of deleting another

**Quiz** blanks a term and offers plausible distractors:
> **1.** A transitive dependency exists when a non-key attribute depends on another ______ rather than on the key itself.
> a) minimize data  b) composite candidate  c) relational model  d) non-key attribute

## Four bugs found while building this

Each was caught by running the tool and reading its output, and each now has a regression test.

1. **Bigrams bridged over short words.** "may not hold a list" produced the term *"hold list"*. The content-word regex requires three characters, so `a`, `on`, `of` were invisible and adjacent-looking words weren't adjacent. Adjacency is now computed over every word.
2. **Bigrams crossed sentence boundaries.** "…non-key attributes. Boyce-Codd normal form…" produced *"attributes boyce-codd"*. N-grams are now built per clause.
3. **Unanswerable quiz questions.** Blanking the only content word out of a short sentence gave `Functional ______`, which tests nothing. Stems now require nine words of surviving context.
4. **Malformed uploads returned HTTP 500.** pypdf raises its own exception types, which the API didn't catch — so a corrupt file read as a server fault. It now returns **422** with the user's filename, and never leaks the server's temp path.

## Tests

```bash
python3 tests/test_pipeline.py     # 15 tests
```

Covering extraction, heading detection, both bigram-adjacency bugs, key-term quality (asserting function words like *every* and *requires* stay out), article stripping, the verbatim-summary guarantee, quiz answerability, every format rendering, and CLI exit codes.

## Limits

- **No OCR.** A scanned PDF raises `ExtractionError` with a clear message rather than returning empty output.
- **TF-IDF needs a corpus.** Sections of one document are a small corpus, so on very short PDFs the IDF signal is weak and some generic terms survive ranking.
- **Heading detection is heuristic.** Documents with no consistent heading style fall back to a single section.
- **English only** — the stopword list and definition patterns are English.

## Skills

Text extraction, TF-IDF with n-grams, extractive summarisation, pattern-based information extraction, CLI and REST API design, HTTP status semantics, Docker packaging, regression testing.
