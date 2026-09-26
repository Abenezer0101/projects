"""assay -- a data quality gate, and an audit of the gate itself.

  assay check  spec.toml data.csv [--quarantine bad.csv] [--clean good.csv] [--json]
  assay audit  spec.toml data.csv [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import mutate
from .engine import Report, read_csv, run, split, write_csv
from .report import render_audit, render_report
from .rules import as_number
from .spec import SpecError, load_spec


def _load(spec_path, data_path):
    suite = load_spec(spec_path)
    data = data_path or suite.source
    if not data:
        raise SpecError("no data file given and the spec has no 'source'")
    rows = read_csv(data)
    refs = {name: read_csv(Path(spec_path).parent / p) for name, p in (suite.refs or {}).items()}
    return suite, rows, refs


def cmd_check(args):
    suite, rows, refs = _load(args.spec, args.data)
    report = run(suite, rows, refs)

    if args.json:
        print(json.dumps(report.as_dict(), indent=2))
    else:
        print(render_report(report, colour=not args.no_colour))

    if args.quarantine or args.clean:
        good, bad = split(rows, report)
        if args.clean:
            write_csv(args.clean, good, list(rows[0].keys()) if rows else [])
        if args.quarantine:
            write_csv(args.quarantine, bad, list(rows[0].keys()) if rows else [])

    # non-zero exit is the whole point: this is meant to gate a pipeline
    return 0 if report.ok else 1


def default_mutations(rows):
    """Pick corruptions that make sense for the columns actually present.

    A shift_decimal on a column of station names would be a corruption the
    suite cannot possibly catch, and scoring it would just deflate the number
    with something meaningless.
    """
    if not rows:
        return []
    cols = list(rows[0].keys())
    numeric, textual = [], []
    for c in cols:
        vals = [r.get(c) for r in rows[:200]]
        hits = sum(1 for v in vals if as_number(v) is not None)
        (numeric if hits > len(vals) * 0.8 else textual).append(c)

    muts = [mutate.duplicate_rows(), mutate.drop_rows()]
    if textual:
        t = textual[0]
        muts += [mutate.blank_out(t), mutate.pad_whitespace(t),
                 mutate.unknown_category(t), mutate.truncate_values(t)]
    if len(textual) >= 2:
        muts.append(mutate.swap_columns(textual[0], textual[1]))
    if numeric:
        n = numeric[0]
        muts += [mutate.blank_out(n), mutate.shift_decimal(n), mutate.rescale(n),
                 mutate.inject_outlier(n), mutate.corrupt_type(n)]
    if len(numeric) >= 2:
        muts.append(mutate.swap_columns(numeric[0], numeric[1]))
    return muts


def cmd_audit(args):
    suite, rows, refs = _load(args.spec, args.data)
    muts = default_mutations(rows)
    result = mutate.audit(suite, rows, muts, refs)

    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    else:
        print(render_audit(result, colour=not args.no_colour))
    # an audit reports; it does not gate. Exit 0 unless asked to be strict.
    if args.fail_under is not None and (result.score or 0) < args.fail_under:
        return 1
    return 0


def build_parser():
    # shared flags live on a parent parser so they work on EITHER side of the
    # subcommand -- `assay --no-colour check x` and `assay check x --no-colour`
    # are both what someone will type, and only one of them working is a bug
    # default=SUPPRESS matters: without it the SUBPARSER writes its own False
    # over the value the parent already parsed, so the flag silently works on
    # only one side of the subcommand. The parser-level default below supplies
    # the baseline instead.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--no-colour", "--no-color", action="store_true",
                        dest="no_colour", default=argparse.SUPPRESS,
                        help="plain output, no ANSI codes")

    p = argparse.ArgumentParser(prog="assay", description=__doc__, parents=[common],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    # a pipe or a CI log is not a terminal, and ANSI escapes in a captured log
    # are noise, so colour is off unless we are actually talking to a terminal
    p.set_defaults(no_colour=not sys.stdout.isatty())
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", parents=[common], help="run a rule suite over a CSV")
    c.add_argument("spec"); c.add_argument("data", nargs="?")
    c.add_argument("--quarantine", help="write failing rows here")
    c.add_argument("--clean", help="write passing rows here")
    c.add_argument("--json", action="store_true")
    c.set_defaults(fn=cmd_check)

    a = sub.add_parser("audit", parents=[common], help="break the data on purpose and see what the rules catch")
    a.add_argument("spec"); a.add_argument("data", nargs="?")
    a.add_argument("--json", action="store_true")
    a.add_argument("--fail-under", type=float, help="exit 1 if the score is below this (0-1)")
    a.set_defaults(fn=cmd_audit)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except SpecError as e:
        print(f"assay: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"assay: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
