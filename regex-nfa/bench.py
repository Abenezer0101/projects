"""The input that makes a backtracking engine fall over.

The pattern is `a?` repeated n times followed by `a` repeated n times, matched
against n letters a -- the standard witness from Cox's "Regular Expression
Matching Can Be Simple And Fast".

Every one of the `a?` groups can match or skip, and the engine has to try the
combinations to discover that only one assignment works. That is 2^n paths.
The NFA keeps the set of reachable states instead, which cannot exceed the
size of the machine, so it walks the input once.

Both engines are given the same pattern and the same string and asked the same
question. The only difference is the algorithm.
"""

from __future__ import annotations

import re
import time

from nfa import Regex

CEILING = 2.0  # seconds; stop asking `re` once it passes this


def pathological(n: int) -> tuple[str, str]:
    return "a?" * n + "a" * n, "a" * n


def timed(fn) -> tuple[bool, float]:
    t0 = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - t0


def main() -> None:
    print("pattern: 'a?' * n + 'a' * n      input: 'a' * n\n")
    print(f"{'n':>4} {'states':>8} {'re (s)':>12} {'nfa (s)':>10} {'ratio':>10}")
    print("-" * 48)
    re_alive = True
    for n in range(2, 31, 2):
        pattern, text = pathological(n)
        compiled = Regex(pattern)
        states = _count_states(compiled)
        nfa_ok, nfa_s = timed(lambda: compiled.fullmatch(text))

        if re_alive:
            rx = re.compile(pattern)
            re_ok, re_s = timed(lambda: rx.fullmatch(text) is not None)
            assert re_ok == nfa_ok, f"engines disagree at n={n}"
            ratio = f"{re_s / nfa_s:>9.0f}x"
            print(f"{n:>4} {states:>8} {re_s:>12.6f} {nfa_s:>10.6f} {ratio:>10}")
            if re_s > CEILING:
                re_alive = False
                print(f"\n  `re` passed {CEILING}s at n={n}; it is not asked again.")
                print(f"  Each further +2 roughly quadruples it.\n")
        else:
            print(f"{n:>4} {states:>8} {'not asked':>12} {nfa_s:>10.6f} {'':>10}")

    print("\nthe NFA's cost tracks n * states, which is quadratic here only")
    print("because the pattern itself grows with n -- per character it is linear")


def _count_states(rx: Regex) -> int:
    seen, stack = set(), [rx.start]
    while stack:
        s = stack.pop()
        if s is None or s._id in seen:
            continue
        seen.add(s._id)
        stack.extend([s.out, s.out1])
    return len(seen)


if __name__ == "__main__":
    main()
