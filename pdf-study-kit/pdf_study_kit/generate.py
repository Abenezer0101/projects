"""Turn an analysed Document into study material.

Five output formats, all Markdown. Each is assembled from text that exists in
the source — nothing is generated, so nothing can be wrong that was not
already in the PDF.
"""
from __future__ import annotations
import random, re
from .extract import Document
from .analyze import tf_idf, summarize, definitions, sentences, key_sentences_for

FORMATS = ("outline", "summary", "glossary", "flashcards", "quiz", "all")


def _header(doc: Document, title: str) -> list[str]:
    return [f"# {title}", "",
            f"*Source: {doc.source} — {doc.word_count:,} words, "
            f"{len(doc.sections)} sections*", ""]


def _usable_stem(stem: str, min_words: int = 9) -> bool:
    """A cloze question needs enough surrounding context to be answerable.

    Blanking the only content word out of a short sentence produces stems like
    "Functional ______", which test nothing.
    """
    return "______" in stem and len(stem.split()) >= min_words


def outline(doc: Document) -> str:
    out = _header(doc, "Outline")
    if not doc.sections:
        out.append("_No headings detected; the document has no clear structure._")
        return "\n".join(out)
    for sec in doc.sections:
        out.append(f"## {sec.title}")
        out.append(f"*{sec.word_count} words*")
        for s in summarize(Document(doc.source, [sec.body], []), 2):
            out.append(f"- {s}")
        out.append("")
    return "\n".join(out)


def summary(doc: Document, n: int = 8) -> str:
    out = _header(doc, "Summary")
    picked = summarize(doc, n)
    if not picked:
        out.append("_Not enough prose to summarise._")
    for s in picked:
        out.append(f"- {s}")
    out += ["", "## Key terms", ""]
    out.append(", ".join(f"**{t}**" for t, _ in tf_idf(doc, 12)))
    return "\n".join(out)


def glossary(doc: Document) -> str:
    out = _header(doc, "Glossary")
    defs = definitions(doc)
    if not defs:
        out.append("_No explicit definitions found. Terms below are the "
                   "highest-weighted by TF-IDF, with a sentence of context._")
        out.append("")
        for term, _ in tf_idf(doc, 10):
            ctx = key_sentences_for(term, doc, 1)
            out.append(f"**{term}** — {ctx[0] if ctx else '(no context sentence found)'}")
            out.append("")
        return "\n".join(out)
    for d in defs:
        out.append(f"**{d.term}** — {d.definition}")
        out.append("")
    return "\n".join(out)


def flashcards(doc: Document, n: int = 12) -> str:
    """Cloze-deletion cards: blank the key term out of a sentence containing it."""
    out = _header(doc, "Flashcards")
    cards = []
    for d in definitions(doc, n):
        cards.append((f"What is **{d.term}**?", d.definition))
    for term, _ in tf_idf(doc, n * 2):
        if len(cards) >= n:
            break
        if any(term.lower() in q.lower() for q, _ in cards):
            continue
        ctx = key_sentences_for(term, doc, 1)
        if not ctx:
            continue
        blanked = re.sub(rf"\b{re.escape(term)}\b", "______", ctx[0], flags=re.I)
        if not _usable_stem(blanked):
            continue
        cards.append((blanked, term))
    if not cards:
        out.append("_Not enough recognisable terms to build cards._")
    for i, (front, back) in enumerate(cards[:n], 1):
        out += [f"**{i}.** {front}", "", f"> {back}", "", "---", ""]
    return "\n".join(out)


def quiz(doc: Document, n: int = 8, seed: int = 0) -> str:
    """Multiple choice: the answer is the blanked term, distractors are other key terms."""
    rng = random.Random(seed)
    terms = [t for t, _ in tf_idf(doc, 30)]
    out = _header(doc, "Practice Quiz")
    if len(terms) < 4:
        out.append("_Too few distinct key terms to build a quiz._")
        return "\n".join(out)
    questions, answers = [], []
    for term in terms:
        if len(questions) >= n:
            break
        ctx = key_sentences_for(term, doc, 1)
        if not ctx:
            continue
        stem = re.sub(rf"\b{re.escape(term)}\b", "______", ctx[0], flags=re.I)
        if not _usable_stem(stem):
            continue
        pool = [t for t in terms if t != term]
        opts = rng.sample(pool, min(3, len(pool))) + [term]
        rng.shuffle(opts)
        questions.append((stem, opts))
        answers.append(opts.index(term))
    for i, ((stem, opts), ans) in enumerate(zip(questions, answers), 1):
        out.append(f"**{i}.** {stem}")
        for j, o in enumerate(opts):
            out.append(f"   {chr(97+j)}) {o}")
        out.append("")
    out += ["---", "", "### Answer key", ""]
    out.append("  ".join(f"{i}. {chr(97+a)}" for i, a in enumerate(answers, 1)))
    return "\n".join(out)


def build(doc: Document, fmt: str = "all", **kw) -> str:
    if fmt not in FORMATS:
        raise ValueError(f"unknown format {fmt!r}; choose from {', '.join(FORMATS)}")
    if fmt == "all":
        return "\n\n".join([outline(doc), summary(doc), glossary(doc),
                            flashcards(doc), quiz(doc)])
    return {"outline": outline, "summary": summary, "glossary": glossary,
            "flashcards": flashcards, "quiz": quiz}[fmt](doc)
