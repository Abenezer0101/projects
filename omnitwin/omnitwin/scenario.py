"""What-if: change some levers, re-run, and report the difference.

A scenario is a plain dict of deltas. Nothing here decides what a change is
worth -- it runs the same simulator twice and subtracts, so a result can always
be traced back to the mechanics in world.py and sim.py.

Every figure is an average over `seeds` independent runs. A single run of a
stochastic simulation is a coin toss dressed as an answer, and the difference
between two single runs is two coin tosses.
"""

from __future__ import annotations

import statistics as st
from dataclasses import dataclass

from .sim import Policy, simulate
from .world import Product, catalogue, expected_demand

SEEDS = 25


@dataclass
class Delta:
    metric: str
    before: float
    after: float

    @property
    def change(self) -> float:
        return self.after - self.before

    @property
    def pct(self):
        return (self.after / self.before - 1.0) if self.before else None


def _mean(outs, attr):
    return st.mean(getattr(o, attr) for o in outs)


def _run(product, policy, days, seeds, **kw):
    return [simulate(product, policy, days=days, seed=s, **kw) for s in range(seeds)]


def apply_scenario(products=None, days=365, seeds=SEEDS,
                   price_change=0.0, ad_change=0.0,
                   lead_time_add=0.0, lead_time_sd_mult=1.0,
                   target_service=0.95, base_ad_spend=300.0,
                   account_for_lt_variance=True):
    """Run the catalogue twice: as-is, then with the levers moved.

    price_change and ad_change are fractions: 0.05 is +5%.
    lead_time_add is in days; lead_time_sd_mult multiplies the variability.
    """
    products = products or catalogue()
    rows, totals = [], {"before": {}, "after": {}}
    agg = {k: [0.0, 0.0] for k in
           ("revenue", "net_profit", "units_sold", "units_lost", "holding_cost")}
    serv = [[], []]

    for p in products:
        base_pol = Policy(price=p.base_price, daily_ad_spend=base_ad_spend,
                          target_service=target_service)
        new_pol = Policy(price=p.base_price * (1 + price_change),
                         daily_ad_spend=base_ad_spend * (1 + ad_change),
                         target_service=target_service)

        before = _run(p, base_pol, days, seeds,
                      account_for_lt_variance=account_for_lt_variance)
        after = _run(p, new_pol, days, seeds,
                     lead_time_mean=p.lead_time_mean + lead_time_add,
                     lead_time_sd=p.lead_time_sd * lead_time_sd_mult,
                     account_for_lt_variance=account_for_lt_variance)

        row = {"sku": p.sku, "name": p.name}
        for k in agg:
            b, a = _mean(before, k), _mean(after, k)
            row[k] = (b, a)
            agg[k][0] += b
            agg[k][1] += a
        row["service_level"] = (_mean(before, "service_level"), _mean(after, "service_level"))
        serv[0].append(row["service_level"][0])
        serv[1].append(row["service_level"][1])
        rows.append(row)

    summary = {k: Delta(k, v[0], v[1]) for k, v in agg.items()}
    summary["service_level"] = Delta("service_level", st.mean(serv[0]), st.mean(serv[1]))
    return {"rows": rows, "summary": summary, "seeds": seeds, "days": days}


def optimal_price(product: Product, ad_spend=300.0, lo=0.2, hi=6.0, steps=291):
    """The price that maximises profit under the stated demand curve.

    Returns (price, profit, status). Status is "interior" for a real optimum,
    or "unbounded" when the search stopped on a boundary.

    Both boundary cases are real and must not be reported as answers:

    - elasticity between -1 and 0 is INELASTIC, so a 1% price rise costs less
      than 1% of volume and modelled profit climbs without bound. The
      "optimum" is then wherever the grid happened to stop. That is a property
      of constant-elasticity demand, not a fact about the product.
    - a narrow grid can simply miss the optimum. With Merino Socks the true
      profit-maximising price is $9.92 and an earlier range started at $11.00,
      so the search returned its own lower bound and looked plausible doing it.
    """
    grid = []
    for i in range(steps):
        mult = lo + (hi - lo) * i / (steps - 1)
        price = product.base_price * mult
        q = expected_demand(product, price, ad_spend)
        grid.append((price, q * (price - product.unit_cost) - ad_spend))
    best_i = max(range(len(grid)), key=lambda i: grid[i][1])
    price, profit = grid[best_i]
    status = "interior" if 0 < best_i < len(grid) - 1 else "unbounded"
    return price, profit, status


def closed_form_price(product: Product):
    """The textbook monopoly price, c * e / (e + 1), where it exists.

    Kept as an independent check on the grid: two routes to the same number,
    so a mistake in either shows up as a disagreement rather than as a
    confident wrong answer.
    """
    e = product.elasticity
    if e >= -1:
        return None
    return product.unit_cost * e / (e + 1)


def optimal_ad_spend(product: Product, price=None, lo=0.0, hi=5000.0, steps=101):
    price = price or product.base_price
    best = None
    for i in range(steps):
        spend = lo + (hi - lo) * i / (steps - 1)
        q = expected_demand(product, price, spend)
        profit = q * (price - product.unit_cost) - spend
        if best is None or profit > best[1]:
            best = (spend, profit)
    return best
