"""Loading a rule suite from TOML.

TOML is stdlib as of Python 3.11, so a validation gate that reads its rules
from a file still installs nothing. That matters more than it sounds: this is
meant to run in CI, in front of a pipeline, and every dependency it carries is
a dependency the thing it guards has to accept.

Spec errors are raised eagerly and name the offending rule. A gate that
silently skips a rule it could not understand is worse than one that will not
start -- it reports a clean run over checks that never executed.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from .rules import (ERROR, WARN, ColumnsExist, Compare, ControlTotal, ForeignKey,
                    InSet, IsType, Matches, NoPadding, NotNull, Range, RowCount, Unique)


class SpecError(ValueError):
    """Raised when a rule suite cannot be understood. Never swallowed."""


KINDS = {
    "not_null": NotNull, "unique": Unique, "in_set": InSet, "range": Range,
    "matches": Matches, "is_type": IsType, "no_padding": NoPadding,
    "compare": Compare, "foreign_key": ForeignKey, "row_count": RowCount,
    "columns_exist": ColumnsExist, "control_total": ControlTotal,
}

# every field a kind understands beyond id/severity/columns
EXTRA = {
    "in_set": {"allowed", "case_sensitive"}, "range": {"min", "max"},
    "matches": {"pattern"}, "is_type": {"type"}, "compare": {"op", "as"},
    "foreign_key": {"ref", "ref_column"}, "row_count": {"min", "max"},
    "control_total": {"stat", "expected", "tolerance"},
}
NEEDS_COLUMNS = {"not_null": 1, "unique": 1, "in_set": 1, "range": 1, "matches": 1,
                 "is_type": 1, "no_padding": 1, "compare": 2, "foreign_key": 1,
                 "columns_exist": 1, "control_total": 1}


class Suite:
    def __init__(self, name, rules, source=None, refs=None):
        self.name = name
        self.rules = rules
        self.source = source
        self.refs = refs or {}

    def __len__(self):
        return len(self.rules)


def _columns(entry, rid):
    cols = entry.get("columns")
    if cols is None and "column" in entry:
        cols = [entry["column"]]
    if cols is None:
        return ()
    if isinstance(cols, str):
        cols = [cols]
    if not all(isinstance(c, str) and c for c in cols):
        raise SpecError(f"rule '{rid}': columns must be non-empty strings")
    return tuple(cols)


def build_rule(entry):
    rid = entry.get("id")
    if not rid:
        raise SpecError("every rule needs an id")
    kind = entry.get("kind")
    if kind not in KINDS:
        known = ", ".join(sorted(KINDS))
        raise SpecError(f"rule '{rid}': unknown kind '{kind}'. Known kinds: {known}")

    severity = entry.get("severity", ERROR)
    if severity not in (ERROR, WARN):
        raise SpecError(f"rule '{rid}': severity must be '{ERROR}' or '{WARN}'")

    cols = _columns(entry, rid)
    need = NEEDS_COLUMNS.get(kind, 0)
    if len(cols) < need:
        raise SpecError(f"rule '{rid}': kind '{kind}' needs {need} column(s), got {len(cols)}")

    known_keys = {"id", "kind", "severity", "column", "columns"} | EXTRA.get(kind, set())
    for k in entry:
        if k not in known_keys:
            raise SpecError(f"rule '{rid}': '{k}' means nothing to kind '{kind}'")

    cls = KINDS[kind]
    kwargs = {"id": rid, "severity": severity, "columns": cols}

    if kind == "in_set":
        allowed = entry.get("allowed")
        if not allowed:
            raise SpecError(f"rule '{rid}': in_set needs a non-empty 'allowed' list")
        kwargs["allowed"] = frozenset(str(a) for a in allowed)
        kwargs["case_sensitive"] = bool(entry.get("case_sensitive", False))
    elif kind in ("range", "row_count"):
        if entry.get("min") is None and entry.get("max") is None:
            raise SpecError(f"rule '{rid}': {kind} needs at least one of min/max")
        kwargs["min"] = entry.get("min")
        kwargs["max"] = entry.get("max")
    elif kind == "matches":
        pattern = entry.get("pattern")
        if not pattern:
            raise SpecError(f"rule '{rid}': matches needs a 'pattern'")
        import re
        try:
            re.compile(pattern)
        except re.error as e:
            raise SpecError(f"rule '{rid}': pattern is not a valid regex ({e})")
        kwargs["pattern"] = pattern
    elif kind == "is_type":
        t = entry.get("type")
        if t not in ("int", "integer", "float", "number", "date", "datetime", "string"):
            raise SpecError(f"rule '{rid}': unsupported type '{t}'")
        kwargs["type"] = t
    elif kind == "compare":
        from .rules import OPS
        op = entry.get("op")
        if op not in OPS:
            raise SpecError(f"rule '{rid}': op must be one of {', '.join(OPS)}")
        kwargs["op"] = op
        kwargs["as_"] = entry.get("as", "auto")
    elif kind == "control_total":
        stat = entry.get("stat", "sum")
        if stat not in ("sum", "mean", "min", "max", "count"):
            raise SpecError(f"rule '{rid}': stat must be sum/mean/min/max/count")
        if entry.get("expected") is None:
            raise SpecError(f"rule '{rid}': control_total needs an 'expected' value")
        tol = entry.get("tolerance", 0.01)
        if not isinstance(tol, (int, float)) or not 0 <= tol < 1:
            raise SpecError(f"rule '{rid}': tolerance must be a fraction in [0, 1)")
        kwargs.update(stat=stat, expected=float(entry["expected"]), tolerance=float(tol))
    elif kind == "foreign_key":
        if not entry.get("ref") or not entry.get("ref_column"):
            raise SpecError(f"rule '{rid}': foreign_key needs 'ref' and 'ref_column'")
        kwargs["ref"] = entry["ref"]
        kwargs["ref_column"] = entry["ref_column"]

    return cls(**kwargs)


def load_spec(path):
    path = Path(path)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise SpecError(f"{path}: not valid TOML ({e})")

    entries = data.get("rule")
    if not entries:
        raise SpecError(f"{path}: no [[rule]] entries -- a suite with no rules "
                        "would report every dataset as clean")
    if not isinstance(entries, list):
        raise SpecError(f"{path}: 'rule' must be a list of [[rule]] tables")

    rules = [build_rule(e) for e in entries]
    ids = [r.id for r in rules]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise SpecError(f"{path}: duplicate rule ids: {', '.join(sorted(dupes))}")

    return Suite(name=data.get("name", path.stem), rules=rules,
                 source=data.get("source"), refs=data.get("refs", {}))
