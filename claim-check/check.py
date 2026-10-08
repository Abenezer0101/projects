"""Re-derive every claim in the registry; exit non-zero if any has rotted.

For each claim, two independent checks:

  PROSE  the claimed string is still present in that project's README
  CODE   running the snippet still prints that string

Both must pass. One without the other is the failure mode this exists to
catch: code that drifts away from its documentation, or documentation edited
to a number the code never produced.

Claims run in parallel subprocesses -- they are independent, each takes a
second or two, and the whole suite is only worth having if it is quick enough
to run before every commit.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from claims import CLAIMS, SKIPPED, Claim

ROOT = pathlib.Path(__file__).resolve().parent.parent
TIMEOUT = 180


@dataclass
class Result:
    claim: Claim
    prose_ok: bool
    code_ok: bool
    derived: str
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.prose_ok and self.code_ok


def check_prose(claim: Claim) -> bool:
    readme = ROOT / claim.project / "README.md"
    if not readme.exists():
        return False
    return claim.claimed in readme.read_text()


def check_code(claim: Claim) -> tuple[bool, str, str]:
    directory = ROOT / claim.project
    if not directory.is_dir():
        return False, "", f"no such project directory: {claim.project}"
    try:
        completed = subprocess.run(
            [sys.executable, "-c", claim.snippet],
            cwd=directory, capture_output=True, text=True, timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return False, "", f"timed out after {TIMEOUT}s"
    if completed.returncode != 0:
        tail = completed.stderr.strip().splitlines()
        return False, "", tail[-1] if tail else "non-zero exit, no stderr"
    derived = completed.stdout.strip()
    return derived == claim.claimed, derived, ""


def verify(claim: Claim) -> Result:
    prose = check_prose(claim)
    code_ok, derived, error = check_code(claim)
    return Result(claim, prose, code_ok, derived, error)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="re-derive every number this repository claims")
    parser.add_argument("--project", help="check only this project")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--quiet", action="store_true",
                        help="print only failures and the summary")
    args = parser.parse_args()

    claims = [c for c in CLAIMS if not args.project or c.project == args.project]
    if not claims:
        print(f"no claims registered for {args.project!r}", file=sys.stderr)
        return 2

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(verify, claims))

    width = max(len(r.claim.project) for r in results)
    failures = [r for r in results if not r.ok]

    current = None
    for result in results:
        if not args.quiet and result.claim.project != current:
            current = result.claim.project
            print(f"\n{current}")
        if result.ok:
            if not args.quiet:
                note = f"   {result.claim.note}" if result.claim.note else ""
                print(f"  ok    {result.claim.claimed:<16}{note}")
            continue
        if args.quiet:
            print(f"{result.claim.project}: {result.claim.claimed}")
        reason = []
        if not result.prose_ok:
            reason.append("README no longer contains this string")
        if not result.code_ok:
            reason.append(result.error or
                          f"code derived {result.derived!r}, README claims "
                          f"{result.claim.claimed!r}")
        for line in reason:
            print(f"  FAIL  {result.claim.claimed:<16} {line}")

    print(f"\n{len(results) - len(failures)} of {len(results)} claims reproduce")
    if SKIPPED and not args.quiet:
        print(f"\n{len(SKIPPED)} claims deliberately not checked:")
        for project, what, why in SKIPPED:
            print(f"  {project}: {what}")
            print(f"      {why}")
    if failures:
        print(f"\n{len(failures)} FAILED", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
