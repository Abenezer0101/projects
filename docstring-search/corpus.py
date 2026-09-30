"""Harvest a real corpus: every public function and class docstring in the
Python standard library.

Real text, no network, and a corpus where relevance judgements can actually be
checked -- if you ask for "read a zip archive" and `zipfile.ZipFile` is not in
the top ten, the search is wrong, and no one has to argue about it.

The harvested corpus is written to corpus.json and committed, so the numbers
in the README reproduce on a machine with a different Python build.
"""

from __future__ import annotations

import importlib
import inspect
import json
import sys
import warnings

MIN_DOC = 60

# `this` prints the Zen on import and `antigravity` opens a web browser.
# Importing a module can run code; these two are the reminder.
SKIP = {"this", "antigravity", "idlelib", "turtle", "turtledemo", "tkinter"}

# packages whose useful callables live one level down
SUBMODULES = ["concurrent.futures", "os.path", "xml.etree.ElementTree",
              "urllib.request", "urllib.parse", "email.message", "http.client",
              "collections.abc", "logging.handlers"]

# A name re-exported from another module stays in the corpus under the name you
# would actually type: secrets.choice and random.choice are both real answers,
# and a search over "what can I call" should be able to return either.


def harvest() -> list[dict]:
    warnings.filterwarnings("ignore")
    docs: list[dict] = []
    names = sorted(sys.stdlib_module_names) + SUBMODULES
    for mod_name in names:
        if mod_name.startswith("_") or mod_name in SKIP:
            continue
        try:
            module = importlib.import_module(mod_name)
        except Exception:
            continue  # platform-specific or deprecated; not an error here
        for name, obj in sorted(vars(module).items()):
            if name.startswith("_"):
                continue
            # isroutine, not isfunction: half the interesting stdlib callables
            # are C builtins or bound methods of a module-level instance, and
            # isfunction silently excludes every one of them. random.sample is
            # a bound method; functools.cmp_to_key is a builtin.
            if not (inspect.isroutine(obj) or inspect.isclass(obj)):
                continue
            try:
                doc = inspect.getdoc(obj) or ""
            except Exception:
                continue
            if len(doc) < MIN_DOC:
                continue
            docs.append({"id": f"{mod_name}.{name}", "module": mod_name, "text": doc})
    return docs


def main() -> None:
    docs = harvest()
    with open("corpus.json", "w") as fh:
        json.dump(docs, fh, indent=0)
    chars = sum(len(d["text"]) for d in docs)
    mods = len({d["module"] for d in docs})
    print(f"{len(docs)} documents from {mods} modules, {chars} characters")


if __name__ == "__main__":
    main()
