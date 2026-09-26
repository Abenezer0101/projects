"""Rendering a run or an audit for a terminal."""

from __future__ import annotations

from .rules import ERROR

GREEN, RED, YELLOW, DIM, BOLD, OFF = (
    "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m")


def _c(text, colour, use):
    return f"{colour}{text}{OFF}" if use else text


def render_report(report, colour=True, examples=2):
    C = lambda t, col: _c(t, col, colour)
    out = [C(f"{report.suite}", BOLD),
           f"  {report.total_rows:,} rows · {len(report.results)} rules"]

    for r in sorted(report.results, key=lambda r: (r.passed, r.rule.severity != ERROR)):
        if r.passed:
            out.append(f"  {C('pass', GREEN)}  {r.rule.id:<26} {C(r.rule.describe(), DIM)}")
            continue
        tag = C("FAIL", RED) if r.rule.severity == ERROR else C("warn", YELLOW)
        out.append(f"  {tag}  {r.rule.id:<26} {len(r.violations):,} "
                   f"({r.rate:.1%})  {C(r.rule.describe(), DIM)}")
        for v in r.violations[:examples]:
            where = "table" if v.row < 0 else f"row {v.row + 1}"
            out.append(C(f"          {where}: {v.value!r} — {v.detail}", DIM))
        if len(r.violations) > examples:
            out.append(C(f"          … {len(r.violations) - examples:,} more", DIM))

    verdict = C("PASS", GREEN) if report.ok else C("FAIL", RED)
    out.append(f"  {verdict}  {report.clean_rows:,} clean, "
               f"{len(report.bad_rows):,} quarantined, {len(report.warnings)} warning(s)")
    return "\n".join(out)


def render_audit(audit, colour=True):
    C = lambda t, col: _c(t, col, colour)
    out = [C("Rule-suite audit", BOLD),
           f"  {audit.rules} rules vs {len(audit.findings)} corruptions"]
    for f in audit.findings:
        if f.caught:
            out.append(f"  {C('caught ', GREEN)} {f.mutation.name:<18} "
                       f"{C(f.mutation.detail, DIM)}  {C('→ ' + ', '.join(f.by), DIM)}")
        else:
            out.append(f"  {C('MISSED ', RED)} {f.mutation.name:<18} {f.mutation.detail}")

    score = audit.score
    pct = "n/a" if score is None else f"{score:.0%}"
    colour_for = GREEN if (score or 0) >= 0.8 else YELLOW if (score or 0) >= 0.5 else RED
    out.append(f"  {C('detection score', BOLD)}: {C(pct, colour_for)} "
               f"({len(audit.caught)}/{len(audit.findings)})")
    if audit.missed:
        out.append(C("  blind to: " + ", ".join(f.mutation.name for f in audit.missed), DIM))
    return "\n".join(out)
