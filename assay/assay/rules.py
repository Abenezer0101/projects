"""Rule types and how a rule decides a row is wrong.

Everything is deliberately explicit. There is no `eval`, no expression
language, and no plugin hook -- a data-quality gate runs against files you did
not write, often in CI, and the least interesting way for one to fail is by
executing something it read out of a config file.

Values arrive as strings, because that is what a CSV actually contains.
Coercion is a rule's own business: `range` decides a value is not a number,
rather than the loader silently deciding it for every rule at once.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

ERROR, WARN = "error", "warn"
NULLISH = {"", "na", "n/a", "null", "none", "nan", "-", "--"}


def is_null(value) -> bool:
    return value is None or str(value).strip().lower() in NULLISH


def as_number(value):
    """Return a float, or None if this is not a number. Tolerates 1,234 and $5."""
    if is_null(value):
        return None
    s = str(value).strip().replace(",", "").replace("$", "").replace("%", "")
    try:
        return float(s)
    except ValueError:
        return None


# `is_type = "datetime"` should mean "this parses as a time", not "this is in
# one of the handful of layouts I happened to list". Enforcing a SINGLE layout
# is a different question, and `matches` is the rule for it -- conflating the
# two turns every legitimate format into a false positive.
DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d",
    "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y",
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y",
    "%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%d-%b-%Y",
    "%b %d, %Y", "%d %B %Y",
)


def as_datetime(value):
    if is_null(value):
        return None
    s = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


@dataclass(frozen=True)
class Violation:
    row: int              # 0-based index into the data rows
    value: str
    detail: str = ""


@dataclass
class RuleResult:
    rule: "Rule"
    violations: list
    checked: int

    @property
    def passed(self) -> bool:
        return not self.violations

    @property
    def rate(self) -> float:
        return len(self.violations) / self.checked if self.checked else 0.0


@dataclass
class Rule:
    """Base rule. Subclasses implement `check`."""
    id: str
    severity: str = ERROR
    columns: tuple = ()

    kind = "rule"

    def describe(self) -> str:
        return self.kind

    def required_columns(self) -> tuple:
        return self.columns

    def check(self, rows, ctx=None) -> list:
        raise NotImplementedError

    def run(self, rows, ctx=None) -> RuleResult:
        return RuleResult(self, self.check(rows, ctx or {}), len(rows))


# ------------------------------------------------------------ column rules

@dataclass
class NotNull(Rule):
    kind = "not_null"

    def describe(self):
        return f"{self.columns[0]} is never empty"

    def check(self, rows, ctx=None):
        col = self.columns[0]
        return [Violation(i, r.get(col, ""), "empty")
                for i, r in enumerate(rows) if is_null(r.get(col))]


@dataclass
class Unique(Rule):
    kind = "unique"

    def describe(self):
        return f"{' + '.join(self.columns)} is unique"

    def check(self, rows, ctx=None):
        seen, out = {}, []
        for i, r in enumerate(rows):
            key = tuple(str(r.get(c, "")).strip() for c in self.columns)
            if all(is_null(k) for k in key):
                continue                      # all-empty keys are not-null's job
            if key in seen:
                out.append(Violation(i, " | ".join(key), f"first seen at row {seen[key]}"))
            else:
                seen[key] = i
        return out


@dataclass
class InSet(Rule):
    allowed: frozenset = frozenset()
    case_sensitive: bool = False
    kind = "in_set"

    def describe(self):
        vals = sorted(self.allowed)
        shown = ", ".join(vals[:4]) + ("…" if len(vals) > 4 else "")
        return f"{self.columns[0]} is one of ({shown})"

    def check(self, rows, ctx=None):
        col = self.columns[0]
        norm = (lambda s: s) if self.case_sensitive else (lambda s: s.lower())
        allowed = {norm(a) for a in self.allowed}
        out = []
        for i, r in enumerate(rows):
            v = r.get(col)
            if is_null(v):
                continue                      # emptiness is not_null's job
            if norm(str(v).strip()) not in allowed:
                out.append(Violation(i, str(v), "not an allowed value"))
        return out


@dataclass
class Range(Rule):
    min: float = None
    max: float = None
    kind = "range"

    def describe(self):
        lo = "-inf" if self.min is None else f"{self.min:g}"
        hi = "inf" if self.max is None else f"{self.max:g}"
        return f"{self.columns[0]} within [{lo}, {hi}]"

    def check(self, rows, ctx=None):
        col, out = self.columns[0], []
        for i, r in enumerate(rows):
            raw = r.get(col)
            if is_null(raw):
                continue
            n = as_number(raw)
            if n is None:
                out.append(Violation(i, str(raw), "not a number"))
            elif self.min is not None and n < self.min:
                out.append(Violation(i, str(raw), f"below {self.min:g}"))
            elif self.max is not None and n > self.max:
                out.append(Violation(i, str(raw), f"above {self.max:g}"))
        return out


@dataclass
class Matches(Rule):
    pattern: str = ".*"
    kind = "matches"

    def describe(self):
        return f"{self.columns[0]} matches /{self.pattern}/"

    def check(self, rows, ctx=None):
        col, rx, out = self.columns[0], re.compile(self.pattern), []
        for i, r in enumerate(rows):
            v = r.get(col)
            if is_null(v):
                continue
            if not rx.fullmatch(str(v).strip()):
                out.append(Violation(i, str(v), "does not match"))
        return out


@dataclass
class IsType(Rule):
    type: str = "string"
    kind = "is_type"

    def describe(self):
        return f"{self.columns[0]} parses as {self.type}"

    def check(self, rows, ctx=None):
        col, out = self.columns[0], []
        for i, r in enumerate(rows):
            v = r.get(col)
            if is_null(v):
                continue
            ok = True
            if self.type in ("int", "integer"):
                n = as_number(v)
                ok = n is not None and float(n).is_integer()
            elif self.type in ("float", "number"):
                ok = as_number(v) is not None
            elif self.type in ("date", "datetime"):
                ok = as_datetime(v) is not None
            if not ok:
                out.append(Violation(i, str(v), f"not {self.type}"))
        return out


@dataclass
class NoPadding(Rule):
    """Leading or trailing whitespace: invisible, and it breaks every join."""
    kind = "no_padding"

    def describe(self):
        return f"{self.columns[0]} has no leading or trailing spaces"

    def check(self, rows, ctx=None):
        col = self.columns[0]
        return [Violation(i, repr(r.get(col)), "padded")
                for i, r in enumerate(rows)
                if r.get(col) is not None and str(r[col]) != str(r[col]).strip()]


# -------------------------------------------------------- relational rules

OPS = {
    "<":  lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">":  lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


@dataclass
class Compare(Rule):
    """Compare two columns in the same row, e.g. ended_at > started_at."""
    op: str = "<"
    as_: str = "auto"
    kind = "compare"

    def describe(self):
        return f"{self.columns[0]} {self.op} {self.columns[1]}"

    def check(self, rows, ctx=None):
        left, right = self.columns[0], self.columns[1]
        fn, out = OPS[self.op], []
        for i, r in enumerate(rows):
            a, b = r.get(left), r.get(right)
            if is_null(a) or is_null(b):
                continue
            pa, pb = _coerce_pair(a, b, self.as_)
            if pa is None or pb is None:
                out.append(Violation(i, f"{a} / {b}", "not comparable"))
            elif not fn(pa, pb):
                out.append(Violation(i, f"{a} / {b}", f"expected {left} {self.op} {right}"))
        return out


def _coerce_pair(a, b, mode):
    if mode in ("number", "auto"):
        na, nb = as_number(a), as_number(b)
        if na is not None and nb is not None:
            return na, nb
        if mode == "number":
            return None, None
    if mode in ("datetime", "date", "auto"):
        da, db = as_datetime(a), as_datetime(b)
        if da is not None and db is not None:
            return da, db
        if mode != "auto":
            return None, None
    if mode == "string":
        return str(a), str(b)
    return None, None


@dataclass
class ForeignKey(Rule):
    """Every value must appear in a reference set supplied at run time."""
    ref: str = ""
    ref_column: str = ""
    kind = "foreign_key"

    def describe(self):
        return f"{self.columns[0]} exists in {self.ref}.{self.ref_column}"

    def check(self, rows, ctx=None):
        ctx = ctx or {}
        ref_rows = (ctx.get("refs") or {}).get(self.ref)
        if ref_rows is None:
            # a missing reference is a broken rule, not a clean dataset
            return [Violation(-1, self.ref, "reference dataset not supplied")]
        known = {str(r.get(self.ref_column, "")).strip() for r in ref_rows}
        col, out = self.columns[0], []
        for i, r in enumerate(rows):
            v = r.get(col)
            if is_null(v):
                continue
            if str(v).strip() not in known:
                out.append(Violation(i, str(v), "no matching reference row"))
        return out


# ------------------------------------------------------------ table rules

@dataclass
class RowCount(Rule):
    min: int = None
    max: int = None
    kind = "row_count"

    def describe(self):
        lo = 0 if self.min is None else self.min
        hi = "inf" if self.max is None else self.max
        return f"row count within [{lo}, {hi}]"

    def check(self, rows, ctx=None):
        n = len(rows)
        if self.min is not None and n < self.min:
            return [Violation(-1, str(n), f"fewer than {self.min} rows")]
        if self.max is not None and n > self.max:
            return [Violation(-1, str(n), f"more than {self.max} rows")]
        return []


@dataclass
class ColumnsExist(Rule):
    kind = "columns_exist"

    def describe(self):
        return f"columns present: {', '.join(self.columns)}"

    def check(self, rows, ctx=None):
        if not rows:
            return []
        have = set(rows[0].keys())
        return [Violation(-1, c, "column missing") for c in self.columns if c not in have]


@dataclass
class ControlTotal(Rule):
    """A column's aggregate must land near a known figure.

    This rule exists because the audit found the hole. A `range` check cannot
    catch a decimal shift: ten times a small state is still a plausible large
    state, so the value sails through a per-row bound while the total moves by
    double digits. Per-row rules are blind to anything that stays individually
    plausible -- only an aggregate sees it.

    It is the oldest trick in data processing: reconcile against a control
    total. Nulls are skipped; `count` counts non-null values.
    """
    stat: str = "sum"
    expected: float = 0.0
    tolerance: float = 0.01       # fractional, so 0.01 is +/-1%
    kind = "control_total"

    def describe(self):
        return (f"{self.stat}({self.columns[0]}) within "
                f"{self.tolerance:.1%} of {self.expected:,g}")

    def check(self, rows, ctx=None):
        col = self.columns[0]
        vals = [n for n in (as_number(r.get(col)) for r in rows) if n is not None]
        if not vals:
            return [Violation(-1, "0 values", f"no numeric values in {col}")]
        actual = {"sum": sum(vals), "mean": sum(vals) / len(vals),
                  "min": min(vals), "max": max(vals),
                  "count": float(len(vals))}[self.stat]
        limit = abs(self.expected) * self.tolerance
        if abs(actual - self.expected) > limit:
            drift = (actual / self.expected - 1) if self.expected else float("inf")
            return [Violation(-1, f"{actual:,.6g}",
                              f"expected {self.expected:,g} +/-{self.tolerance:.1%} "
                              f"({drift:+.1%} off)")]
        return []
