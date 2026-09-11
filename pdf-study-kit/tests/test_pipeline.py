"""Tests for the study-kit pipeline.  python3 tests/test_pipeline.py"""
import pathlib, sys, subprocess
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from pdf_study_kit import extract, build, tf_idf, definitions, FORMATS
from pdf_study_kit.extract import ExtractionError, looks_like_heading, split_sections
from pdf_study_kit.analyze import ngrams, sentences
from pdf_study_kit.generate import _usable_stem

PDF = pathlib.Path(__file__).resolve().parents[1] / "examples" / "database_normalization.pdf"


def test_extract_finds_text_and_sections():
    d = extract(PDF)
    assert d.word_count > 300, d.word_count
    assert len(d.sections) >= 3, [s.title for s in d.sections]


def test_missing_file_raises():
    try:
        extract("nope.pdf"); assert False, "should have raised"
    except FileNotFoundError:
        pass


def test_heading_detection():
    assert looks_like_heading("2. Functional Dependency")
    assert looks_like_heading("THE NORMAL FORMS")
    assert not looks_like_heading(
        "A functional dependency is a constraint between two sets of attributes.")


def test_sections_need_body():
    secs = split_sections("1. Tiny\nshort\n2. Also Tiny\nalso short")
    assert secs == [], secs          # nothing meets the 20-word floor


def test_bigrams_do_not_cross_dropped_words():
    """'hold a list' must not become the bigram 'hold list'."""
    g = ngrams("A column may not hold a list of values")
    assert "hold list" not in g, g


def test_bigrams_do_not_cross_sentences():
    g = ngrams("...non-key attributes. Boyce-Codd normal form is stricter")
    assert "attributes boyce-codd" not in g, g
    assert "boyce-codd normal" in g, g


def test_key_terms_are_content_words():
    d = extract(PDF)
    terms = [t for t, _ in tf_idf(d, 12)]
    for junk in ("every", "requires", "value", "another", "second"):
        assert junk not in terms, f"{junk!r} leaked into key terms: {terms}"
    assert any(" " in t for t in terms), f"expected a bigram among {terms}"


def test_definitions_strip_leading_articles():
    d = extract(PDF)
    defs = definitions(d)
    assert defs, "no definitions found"
    for x in defs:
        first = x.term.split()[0].lower()
        assert first not in ("a", "an", "the"), x.term


def test_summary_sentences_are_verbatim():
    """Extractive means every output sentence exists in the source."""
    d = extract(PDF)
    body = " ".join(d.text.split())
    for line in build(d, "summary").splitlines():
        if line.startswith("- "):
            assert " ".join(line[2:].split()) in body, line


def test_quiz_stems_are_answerable():
    assert not _usable_stem("Functional ______")
    assert _usable_stem("A ______ is a minimal set of attributes that determines the rest.")


def test_quiz_has_answer_key():
    out = build(extract(PDF), "quiz")
    assert "Answer key" in out and "**1.**" in out


def test_every_format_renders():
    d = extract(PDF)
    for fmt in FORMATS:
        text = build(d, fmt)
        assert len(text) > 100, f"{fmt} produced {len(text)} chars"


def test_unknown_format_rejected():
    try:
        build(extract(PDF), "podcast"); assert False, "should have raised"
    except ValueError:
        pass


def test_cli_runs():
    r = subprocess.run([sys.executable, "-m", "pdf_study_kit", "--pdf", str(PDF),
                        "--format", "summary"], capture_output=True, text=True,
                       cwd=str(PDF.parents[1]))
    assert r.returncode == 0, r.stderr
    assert "# Summary" in r.stdout


def test_cli_missing_file_exits_nonzero():
    r = subprocess.run([sys.executable, "-m", "pdf_study_kit", "--pdf", "nope.pdf"],
                       capture_output=True, text=True, cwd=str(PDF.parents[1]))
    assert r.returncode == 2, (r.returncode, r.stderr)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1; print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            failed += 1; print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests)-failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)
