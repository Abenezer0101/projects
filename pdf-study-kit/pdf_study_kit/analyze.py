"""Deterministic text analysis — no model, no API key.

Three classical techniques do the work an LLM would otherwise be asked for:

  * TF-IDF over sections   -> which terms actually matter in this document
  * Sentence scoring       -> extractive summary (pick real sentences, never
                              generate them, so nothing can be hallucinated)
  * Definition patterns    -> glossary and flashcards

Extractive summarisation has a real advantage over generative here: every
sentence in the output appears verbatim in the source, so a study guide can
never invent a fact.
"""
from __future__ import annotations
import math, re
from collections import Counter
from dataclasses import dataclass

from .extract import Document, Section

STOPWORDS = set("""
a an the and or but if then else when while of in on at to from by for with about
against between into through during before after above below up down out off over
under again further once here there all any both each few more most other some such
no nor not only own same so than too very can will just should now is are was were be
been being have has had do does did doing would could may might must shall this that
these those it its their they them he she his her we us our you your i me my as also
which who whom whose what where why how because however therefore thus hence within
per via upon across among along around since until whether either neither
every each one two three many much several few various certain given
requires require required requiring uses used using include includes including
contain contains containing provide provides another second third first last
set sets part parts value values type types way ways case cases thing things
example examples number numbers form forms make makes made take takes
""".split())

_WORD = re.compile(r"[A-Za-z][A-Za-z\-']{2,}")
_ANYWORD = re.compile(r"[A-Za-z][A-Za-z\-']*")   # includes short words, for adjacency
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")

# "X is a Y", "X refers to Y", "X is defined as Y", "X, which is Y"
_DEFN = re.compile(
    r"\b(?P<term>[A-Z][\w\- ]{2,45}?)\s+"
    r"(?:is|are|was|were)\s+(?:a|an|the)?\s*(?:defined as|known as|called|referred to as)\s+"
    r"(?P<body>.+?)[.;]", re.I)
_DEFN2 = re.compile(
    r"\b(?P<term>[A-Z][\w\- ]{2,45}?)\s+(?:is|are)\s+(?P<body>a|an|the)\s+(?P<rest>.+?)[.;]")


def tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text) if w.lower() not in STOPWORDS]


def ngrams(text: str) -> list[str]:
    """Unigrams plus adjacent bigrams of content words.

    Technical vocabulary is mostly two words -- "normal form", "functional
    dependency", "candidate key". Scoring only unigrams splits those into
    halves that individually mean little.

    Adjacency is computed over *every* word, including short ones, and never
    crosses a clause boundary. Using the content-word regex here instead would
    silently bridge dropped words ("hold a list" -> "hold list") and sentence
    breaks ("attributes. Boyce-Codd" -> "attributes boyce-codd").
    """
    out: list[str] = []
    for chunk in re.split(r"[.;:!?()\[\]]", text):
        words = [w.lower() for w in _ANYWORD.findall(chunk)]
        keep = lambda w: len(w) >= 3 and w not in STOPWORDS
        out.extend(w for w in words if keep(w))
        for a, b in zip(words, words[1:]):
            if keep(a) and keep(b):
                out.append(f"{a} {b}")
    return out


def sentences(text: str) -> list[str]:
    out = []
    for s in _SENT.split(text):
        s = s.strip()
        if 40 <= len(s) <= 400 and s[0].isupper():
            out.append(s)
    return out


def tf_idf(doc: Document, top_n: int = 20) -> list[tuple[str, float]]:
    """Rank terms by TF-IDF across the document's own sections.

    Sections act as the corpus, so a word appearing everywhere (common to the
    whole paper) scores lower than one concentrated in a few sections.
    """
    units = [s.body for s in doc.sections] or doc.pages
    units = [u for u in units if u.strip()]
    if not units:
        return []
    tokenised = [ngrams(u) for u in units]
    df = Counter()
    for toks in tokenised:
        df.update(set(toks))
    n = len(units)
    total = Counter()
    for toks in tokenised:
        tf = Counter(toks)
        length = max(len(toks), 1)
        for term, count in tf.items():
            idf = math.log((n + 1) / (df[term] + 1)) + 1
            weight = (count / length) * idf
            if " " in term:
                weight *= 1.6          # a matched two-word term is more informative
            total[term] = max(total[term], weight)

    ranked = [t for t, _ in total.most_common(top_n * 3)]
    covered, out = set(), []
    for term in ranked:
        if " " in term:
            covered.update(term.split())
    for term in ranked:
        if " " not in term and term in covered:
            continue                   # drop halves of a bigram we already kept
        out.append((term, total[term]))
        if len(out) >= top_n:
            break
    return out


def summarize(doc: Document, max_sentences: int = 8) -> list[str]:
    """Extractive summary: score every sentence, keep the best, restore order.

    Score = sum of key-term weights it contains, normalised by length so long
    sentences do not win automatically, with a small bonus for appearing early
    in a section (where topic sentences live).
    """
    weights = dict(tf_idf(doc, 40))
    if not weights:
        return []
    scored = []
    for sec in (doc.sections or [Section("Body", doc.text)]):
        sents = sentences(sec.body)
        for i, s in enumerate(sents):
            toks = ngrams(s)
            if not toks:
                continue
            score = sum(weights.get(t, 0) for t in toks) / math.sqrt(len(toks))
            score *= 1.15 if i == 0 else 1.0
            scored.append((score, len(scored), s))
    scored.sort(key=lambda x: -x[0])
    picked = sorted(scored[:max_sentences], key=lambda x: x[1])
    return [s for _, _, s in picked]


@dataclass
class Definition:
    term: str
    definition: str


def definitions(doc: Document, limit: int = 15) -> list[Definition]:
    """Pull explicit definitions using sentence patterns."""
    found, seen = [], set()
    for sent in sentences(doc.text):
        for pat in (_DEFN, _DEFN2):
            m = pat.search(sent)
            if not m:
                continue
            term = re.sub(r"^(?:a|an|the)\s+", "", m.group("term").strip().rstrip(","), flags=re.I)
            if len(term.split()) > 6 or term.lower() in seen:
                continue
            body = (m.groupdict().get("rest") or m.group("body")).strip()
            if len(body) < 15:
                continue
            seen.add(term.lower())
            found.append(Definition(term, body[:240]))
            break
        if len(found) >= limit:
            break
    return found


def key_sentences_for(term: str, doc: Document, limit: int = 2) -> list[str]:
    t = term.lower()
    return [s for s in sentences(doc.text) if t in s.lower()][:limit]
