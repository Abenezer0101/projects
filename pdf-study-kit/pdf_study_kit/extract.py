"""PDF text extraction and structural parsing.

Everything downstream depends on this, so it is deliberately conservative:
it recovers text and headings, and reports honestly when a PDF has none
(a scanned document) rather than returning empty strings that look like
a successful parse.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path


class ExtractionError(RuntimeError):
    """Raised when a PDF yields no usable text."""


@dataclass
class Section:
    title: str
    body: str

    @property
    def word_count(self) -> int:
        return len(self.body.split())


@dataclass
class Document:
    source: str
    pages: list[str] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(self.pages)

    @property
    def word_count(self) -> int:
        return len(self.text.split())


# A heading: short, not ending in a sentence period, often numbered or titlecase.
_NUMBERED = re.compile(r"^\s*(\d+(\.\d+)*)[.)]?\s+(\S.*)$")
_LIGATURES = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", "’": "'", "“": '"', "”": '"'}


def _tidy(raw: str) -> str:
    for bad, good in _LIGATURES.items():
        raw = raw.replace(bad, good)
    raw = re.sub(r"-\n(\w)", r"\1", raw)          # re-join hyphenated line breaks
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.strip()


def looks_like_heading(line: str) -> bool:
    line = line.strip()
    if not (3 <= len(line) <= 90):
        return False
    if line.endswith((".", ",", ";", ":")) and not _NUMBERED.match(line):
        return False
    if _NUMBERED.match(line):
        return True
    words = line.split()
    if len(words) > 12:
        return False
    caps = sum(1 for w in words if w[:1].isupper())
    return line.isupper() or caps >= max(1, int(len(words) * 0.6))


def split_sections(text: str) -> list[Section]:
    """Group body text under detected headings. Unheaded text lands in 'Introduction'."""
    sections, title, buf = [], "Introduction", []
    for line in text.splitlines():
        if looks_like_heading(line):
            if buf and " ".join(buf).strip():
                sections.append(Section(title, " ".join(buf).strip()))
            title, buf = line.strip(), []
        else:
            buf.append(line)
    if buf and " ".join(buf).strip():
        sections.append(Section(title, " ".join(buf).strip()))
    return [s for s in sections if s.word_count >= 20]


def extract(path: str | Path, display_name: str | None = None) -> Document:
    """Read a PDF into a Document. Raises ExtractionError on scanned/empty files."""
    from pypdf import PdfReader

    path = Path(path)
    name = display_name or path.name
    if not path.exists():
        raise FileNotFoundError(path)
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        # pypdf raises its own error types for malformed files. Callers (and
        # the HTTP layer) should see one exception type meaning "bad input",
        # not a library-specific class that reads as a server fault.
        raise ExtractionError(f"{name} is not a readable PDF: {exc}") from exc
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:                       # pragma: no cover
            raise ExtractionError(f"{name} is password-protected") from exc

    pages = [_tidy(p.extract_text() or "") for p in reader.pages]
    doc = Document(source=name, pages=pages)
    if doc.word_count < 50:
        raise ExtractionError(
            f"{name} yielded only {doc.word_count} words — it is probably a "
            "scanned image. This tool does not do OCR."
        )
    doc.sections = split_sections(doc.text)
    return doc
