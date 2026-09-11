"""Command line interface.  python -m pdf_study_kit --pdf paper.pdf"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

from . import __version__
from .extract import extract, ExtractionError
from .generate import build, FORMATS


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="pdf-study-kit",
        description="Turn a PDF into an outline, summary, glossary, flashcards or quiz — offline.")
    p.add_argument("--pdf", required=True, help="path to the PDF")
    p.add_argument("--format", default="all", choices=FORMATS,
                   help="what to generate (default: all)")
    p.add_argument("--out", help="write to this file instead of stdout")
    p.add_argument("--sentences", type=int, default=8, help="summary length")
    p.add_argument("--seed", type=int, default=0, help="quiz shuffle seed")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    a = p.parse_args(argv)

    try:
        doc = extract(a.pdf)
    except FileNotFoundError:
        print(f"error: no such file: {a.pdf}", file=sys.stderr); return 2
    except ExtractionError as e:
        print(f"error: {e}", file=sys.stderr); return 3

    text = build(doc, a.format)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out} ({len(text.splitlines())} lines) from "
              f"{doc.source} — {doc.word_count:,} words, {len(doc.sections)} sections")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
