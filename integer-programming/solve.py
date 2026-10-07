"""Solve both instances and report the bound, the optimum, and the gap."""

from __future__ import annotations

from ip import branch_and_bound, brute_force, round_up_relaxation
from problems import (REQUIRED_RAM, REQUIRED_VCPU, complement_cover,
                      instance_sizing, predicted_cover_gap)


def main() -> None:
    cost, constraints, upper, names = instance_sizing()
    print(f"cheapest instance mix for {REQUIRED_VCPU} vCPU and {REQUIRED_RAM} GB RAM\n")

    bb = branch_and_bound(cost, constraints, upper)
    bf = brute_force(cost, constraints, upper)
    ru = round_up_relaxation(cost, constraints, upper)

    print(f"  LP relaxation      {float(bb.lp_bound):>8.2f}   (fractional, so not buyable)")
    print(f"  round the LP up    {float(ru.cost):>8.2f}   {dict(zip(names, ru.x))}")
    print(f"  integer optimum    {float(bb.cost):>8.2f}   {dict(zip(names, bb.x))}")
    print(f"  brute force        {float(bf.cost):>8.2f}   agrees: {bb.x == bf.x}")

    overpay = (ru.cost - bb.cost) / bb.cost
    gap = (bb.cost - bb.lp_bound) / bb.lp_bound
    print(f"\n  integrality gap    {float(gap):>8.2%}   (optimum above the bound)")
    print(f"  cost of rounding   {float(overpay):>8.2%}   (round-up above the optimum)")
    print(f"\n  search: {bb.nodes} nodes explored, {bb.pruned_by_bound} subtrees "
          f"cut by the bound")
    print(f"          brute force visited {bf.nodes} points "
          f"({bf.nodes / bb.nodes:.0f}x more)")

    print("\n\nwhere the relaxation is much weaker: cover by complements\n")
    print(f"  {'n':>3} {'LP':>7} {'integer':>8} {'gap':>8}")
    for n in (3, 4, 5):
        c, cons, up, _ = complement_cover(n)
        r = branch_and_bound(c, cons, up)
        print(f"  {n:>3} {str(r.lp_bound):>7} {int(r.cost):>8} "
              f"{float(r.cost / r.lp_bound):>7.3f}x")
    print("\n  closed form, n/(n-1) against 2, so the gap tends to 2x:")
    for n in (10, 1000, 10 ** 6):
        lp, ip = predicted_cover_gap(n)
        print(f"    n={n:<8} LP={float(lp):.6f}  integer={ip}  "
              f"gap={ip / float(lp):.4f}x")


if __name__ == "__main__":
    main()
