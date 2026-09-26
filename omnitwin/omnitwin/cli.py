"""omnitwin -- simulate the company before you change it.

  python3 -m omnitwin.cli whatif --price +5 --ads -20
  python3 -m omnitwin.cli whatif --lead-time +14 --lead-time-sd x2 --blind
  python3 -m omnitwin.cli optimise
  python3 -m omnitwin.cli service
  python3 -m omnitwin.cli catalogue
"""

from __future__ import annotations

import argparse
import sys

from .scenario import apply_scenario, closed_form_price, optimal_ad_spend, optimal_price
from .sim import Policy, Z, safety_stock, simulate
from .world import catalogue


def _pct(s):
    """Accept +5, -20, 5% as fractions."""
    return float(str(s).replace("%", "").replace("+", "")) / 100.0


def _mult(s):
    return float(str(s).lower().lstrip("x"))


def cmd_whatif(args):
    r = apply_scenario(price_change=_pct(args.price), ad_change=_pct(args.ads),
                       lead_time_add=args.lead_time, lead_time_sd_mult=_mult(args.lead_time_sd),
                       target_service=args.service, seeds=args.seeds,
                       account_for_lt_variance=not args.blind)
    s = r["summary"]
    print(f"{len(r['rows'])} products, {r['days']} days, mean of {r['seeds']} runs")
    if args.blind:
        print("planner is using AVERAGE lead time only (--blind)")
    print()
    print(f"{'metric':<16} {'before':>16} {'after':>16} {'change':>14}")
    print("-" * 66)
    for k in ("revenue", "net_profit", "units_sold", "units_lost",
              "holding_cost", "service_level"):
        d = s[k]
        pct = f"{d.pct:+.2%}" if d.pct is not None else "n/a"
        if k == "service_level":
            print(f"{k:<16} {d.before:>15.2%} {d.after:>15.2%} {pct:>14}")
        else:
            print(f"{k:<16} {d.before:>16,.0f} {d.after:>16,.0f} {pct:>14}")

    print(f"\n{'product':<18} {'profit before':>15} {'profit after':>14} {'change':>10}")
    print("-" * 60)
    for row in r["rows"]:
        b, a = row["net_profit"]
        print(f"{row['name']:<18} {b:>15,.0f} {a:>14,.0f} {(a/b-1) if b else 0:>10.1%}")
    return 0


def cmd_optimise(args):
    print(f"{'product':<18} {'base':>9} {'profit price':>13} {'closed form':>12} "
          f"{'status':<11} {'ad/day':>9}")
    print("-" * 78)
    for p in catalogue():
        price, _, status = optimal_price(p, ad_spend=0.0)
        cf = closed_form_price(p)
        spend, _ = optimal_ad_spend(p)
        cfs = f"{cf:.2f}" if cf else "none"
        shown = f"{price:.2f}" if status == "interior" else "-"
        print(f"{p.name:<18} {p.base_price:>9.2f} {shown:>13} {cfs:>12} "
              f"{status:<11} {spend:>9,.0f}")
    print("\n'unbounded' means elasticity is between -1 and 0: demand is inelastic,")
    print("so modelled profit rises with price forever and there is no optimum to")
    print("report. That is the demand curve's shape, not advice to raise prices.")
    return 0


def cmd_service(args):
    print("what a service-level target actually costs and earns\n")
    for p in catalogue()[:args.top]:
        ratio = p.margin / (p.unit_cost * p.holding_cost_rate)
        print(f"{p.name}  (a lost sale costs {ratio:.0f}x holding a unit for a year)")
        print(f"   {'target':>8} {'achieved':>10} {'avg inv':>9} {'lost':>8} {'net profit':>13}")
        best = None
        for t in sorted(Z):
            pol = Policy(price=p.base_price, daily_ad_spend=300, target_service=t)
            outs = [simulate(p, pol, days=365, seed=s) for s in range(args.seeds)]
            prof = sum(o.net_profit for o in outs) / len(outs)
            serv = sum(o.service_level for o in outs) / len(outs)
            inv = sum(o.avg_inventory for o in outs) / len(outs)
            lost = sum(o.units_lost for o in outs) / len(outs)
            print(f"   {t:>8.1%} {serv:>10.2%} {inv:>9,.0f} {lost:>8,.0f} {prof:>13,.0f}")
            if best is None or prof > best[1]:
                best = (t, prof)
        print(f"   -> profit peaks at {best[0]:.1%}\n")
    return 0


def cmd_catalogue(args):
    print(f"{'sku':<10} {'name':<18} {'price':>8} {'cost':>7} {'elast':>7} "
          f"{'lead time':>12} {'ad ceiling':>11}")
    print("-" * 80)
    for p in catalogue():
        print(f"{p.sku:<10} {p.name:<18} {p.base_price:>8.2f} {p.unit_cost:>7.2f} "
              f"{p.elasticity:>7.1f} {p.lead_time_mean:>6.0f}+/-{p.lead_time_sd:<4.0f} "
              f"{p.ad_max_lift:>11.2f}")
    print("\nThese parameters are PLANTED, not estimated. Recovering them from")
    print("generated history proves the estimator works; it says nothing about")
    print("any real company.")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="omnitwin", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("whatif", help="move the levers and compare")
    w.add_argument("--price", default="0", help="percent change, e.g. +5")
    w.add_argument("--ads", default="0", help="percent change, e.g. -20")
    w.add_argument("--lead-time", type=float, default=0.0, help="days to add")
    w.add_argument("--lead-time-sd", default="x1", help="multiply variability, e.g. x3")
    w.add_argument("--service", type=float, default=0.95)
    w.add_argument("--seeds", type=int, default=15)
    w.add_argument("--blind", action="store_true",
                   help="plan with average lead time only")
    w.set_defaults(fn=cmd_whatif)

    o = sub.add_parser("optimise", help="profit-maximising price and ad spend")
    o.set_defaults(fn=cmd_optimise)

    s = sub.add_parser("service", help="sweep the service-level target")
    s.add_argument("--top", type=int, default=2)
    s.add_argument("--seeds", type=int, default=15)
    s.set_defaults(fn=cmd_service)

    c = sub.add_parser("catalogue", help="the products and their parameters")
    c.set_defaults(fn=cmd_catalogue)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except ValueError as e:
        print(f"omnitwin: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
