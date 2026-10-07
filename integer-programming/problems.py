"""Two instances: one realistic with a small gap, one built to have a large one.

The first is the kind of problem the method is for. The second exists because
a single instance with a 1.2% gap would invite the conclusion that the LP
relaxation is basically the answer, and that is false in general.
"""

from __future__ import annotations

from fractions import Fraction

# name, vCPU, RAM GB, price per hour (cents)
INSTANCE_TYPES = [
    ("small", 2, 8, 24),
    ("medium", 4, 16, 45),
    ("large", 8, 32, 88),
    ("ram-opt", 4, 32, 70),
    ("cpu-opt", 16, 32, 150),
]
REQUIRED_VCPU = 60
REQUIRED_RAM = 200


def instance_sizing() -> tuple[list, list, list, list[str]]:
    cost = [t[3] for t in INSTANCE_TYPES]
    constraints = [
        ([t[1] for t in INSTANCE_TYPES], REQUIRED_VCPU),
        ([t[2] for t in INSTANCE_TYPES], REQUIRED_RAM),
    ]
    upper = [30, 15, 8, 8, 4]
    names = [t[0] for t in INSTANCE_TYPES]
    return cost, constraints, upper, names


def complement_cover(n: int = 6) -> tuple[list, list, list, list[str]]:
    """Set cover where each set is the complement of one singleton.

    Element e is covered by every set except the one that excludes it, so n-1
    of the n sets. The LP can therefore put 1/(n-1) on every set and satisfy
    each element exactly, for a total of n/(n-1) -- just over 1. Any INTEGER
    cover needs 2 sets, because one set always misses an element.

    So the gap approaches 2x from below as n grows, and it is a gap in the
    relaxation itself rather than an artifact of rounding.
    """
    cost = [1] * n
    constraints = []
    for element in range(n):
        # coefficient 1 on every set that covers this element
        row = [0 if s == element else 1 for s in range(n)]
        constraints.append((row, 1))
    upper = [1] * n
    names = [f"all-but-{i}" for i in range(n)]
    return cost, constraints, upper, names


def predicted_cover_gap(n: int) -> tuple[Fraction, int]:
    """Closed form: the LP optimum and the integer optimum."""
    return Fraction(n, n - 1), 2
