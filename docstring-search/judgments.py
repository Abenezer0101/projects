"""Hand-labelled relevance: which documents genuinely answer each query.

Written by reading the docstrings, not by running either search and blessing
whatever came back -- that would measure agreement with the system under test.
`validate()` asserts every labelled id exists in the corpus, so a typo shows
up as a failure instead of quietly costing the ranker precision.

Relevant means: a developer with this question would be correctly served by
this function or class. Near-misses are deliberately excluded. `gzip.open`
does not open a zip archive.
"""

from __future__ import annotations

JUDGEMENTS: dict[str, set[str]] = {
    "parse command line arguments": {
        "argparse.ArgumentParser", "getopt.getopt", "getopt.gnu_getopt",
    },
    "read a zip archive": {
        "zipfile.ZipFile", "zipfile.is_zipfile", "zipfile.Path",
        "shutil.unpack_archive",
    },
    "create a temporary file": {
        "tempfile.NamedTemporaryFile", "tempfile.TemporaryFile",
        "tempfile.mkstemp", "tempfile.SpooledTemporaryFile",
        "tempfile.TemporaryDirectory", "tempfile.mkdtemp",
    },
    "run an external command": {
        "subprocess.run", "subprocess.Popen", "subprocess.call",
        "subprocess.check_output", "subprocess.check_call",
        "subprocess.getoutput", "subprocess.getstatusoutput",
    },
    "least recently used cache": {"functools.lru_cache", "functools.cache"},
    "deep copy an object": {"copy.deepcopy"},
    "random sample without replacement": {"random.sample"},
    "substitute text with a regular expression": {"re.sub", "re.subn"},
    "iterate over every combination of items": {
        "itertools.combinations", "itertools.permutations", "itertools.product",
        "itertools.combinations_with_replacement",
    },
    "show the difference between two sequences": {
        "difflib.SequenceMatcher", "difflib.unified_diff", "difflib.ndiff",
        "difflib.context_diff", "difflib.Differ", "difflib.HtmlDiff",
        "difflib.diff_bytes",
    },
    "walk a directory tree": {"os.walk", "os.fwalk"},
    # multiprocessing.Pool's docstring is 29 characters and cmp_to_key's is 45,
    # both under the corpus threshold, so neither is in the index and neither
    # can be labelled relevant. concurrent.futures.ProcessPoolExecutor is
    # absent for a different reason: the module resolves it lazily through
    # __getattr__, so it is not in vars() until something touches it.
    "spread work over multiple processes": {
        "multiprocessing.Process", "concurrent.futures.Executor",
        "concurrent.futures.as_completed", "concurrent.futures.wait",
    },
    "sort using a custom comparison function": {
        "operator.itemgetter", "operator.attrgetter", "operator.methodcaller",
    },
    "generate a secure random token": {
        "secrets.token_hex", "secrets.token_bytes", "secrets.token_urlsafe",
        "secrets.SystemRandom",
    },
    "measure how long code takes to run": {
        "timeit.timeit", "timeit.repeat", "timeit.Timer", "cProfile.run",
        "profile.run",
    },
    "match a filename against a wildcard pattern": {
        "fnmatch.fnmatch", "fnmatch.fnmatchcase", "fnmatch.filter",
        "glob.glob", "glob.iglob",
    },
}


def validate(docs: list[dict]) -> tuple[int, list[str]]:
    """Every labelled id must exist in the corpus. Returns (kept, dropped)."""
    have = {d["id"] for d in docs}
    dropped = []
    kept = 0
    for query, relevant in JUDGEMENTS.items():
        for doc_id in sorted(relevant):
            if doc_id in have:
                kept += 1
            else:
                dropped.append(f"{query!r}: {doc_id}")
    return kept, dropped
