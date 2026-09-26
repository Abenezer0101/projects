"""Day-by-day simulation of one product: demand, inventory, and money.

The inventory policy is a continuous-review reorder point, the standard
textbook one, because the interesting behaviour is not in the policy -- it is
in what feeds it.

Safety stock has to cover the demand that arrives during a replenishment lead
time, and the variance of that quantity is

    var(demand over lead time) = E[LT] * var(D) + E[D]^2 * var(LT)

The second term is why lead-time VARIABILITY hurts so much more than lead-time
LENGTH: it is multiplied by the square of mean demand. A high-volume product
with an erratic supplier needs far more safety stock than the same product
with a slower but dependable one, and no amount of staring at average lead
time reveals that.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .world import Product, expected_demand, seasonality_factor

# service-level multipliers, from the standard normal
Z = {0.50: 0.000, 0.80: 0.842, 0.90: 1.282, 0.95: 1.645, 0.975: 1.960, 0.99: 2.326}


@dataclass
class Policy:
    price: float
    daily_ad_spend: float
    target_service: float = 0.95
    review_days: int = 1
    order_multiple: int = 1


@dataclass
class Outcome:
    days: int
    units_sold: int = 0
    units_lost: int = 0
    revenue: float = 0.0
    cogs: float = 0.0
    ad_spend: float = 0.0
    holding_cost: float = 0.0
    stockout_days: int = 0
    inventory_days: float = 0.0
    orders_placed: int = 0

    @property
    def gross_profit(self) -> float:
        return self.revenue - self.cogs

    @property
    def net_profit(self) -> float:
        return self.gross_profit - self.ad_spend - self.holding_cost

    @property
    def service_level(self) -> float:
        total = self.units_sold + self.units_lost
        return self.units_sold / total if total else 1.0

    @property
    def avg_inventory(self) -> float:
        return self.inventory_days / self.days if self.days else 0.0

    @property
    def fill_rate(self) -> float:
        return self.service_level

    def as_dict(self):
        return {"days": self.days, "units_sold": self.units_sold,
                "units_lost": self.units_lost, "revenue": round(self.revenue, 2),
                "net_profit": round(self.net_profit, 2),
                "service_level": round(self.service_level, 4),
                "avg_inventory": round(self.avg_inventory, 1),
                "stockout_days": self.stockout_days,
                "orders_placed": self.orders_placed}


def demand_sd(mean: float, cv: float = 0.35) -> float:
    """Day-to-day demand noise, as a coefficient of variation."""
    return mean * cv


def safety_stock(p: Product, daily_demand: float, service: float, cv: float = 0.35,
                 account_for_lt_variance: bool = True) -> float:
    """z * sd(demand over lead time), with BOTH sources of variance.

    Set account_for_lt_variance=False to model the planner who only knows the
    AVERAGE lead time -- the default in most spreadsheets, and in a good deal
    of software. The supplier is exactly as erratic either way; the buffer just
    stops covering it.
    """
    # NOT `Z.get(service) or Z[0.95]`: Z[0.50] is 0.0, which is falsy, so a
    # legitimate zero-safety-stock target silently became the 95% multiplier
    # and every 50% run reported 95% numbers.
    if service not in Z:
        raise ValueError(f"service must be one of {sorted(Z)}, got {service}")
    z = Z[service]
    var_d = demand_sd(daily_demand, cv) ** 2
    lt_var = (p.lead_time_sd ** 2) if account_for_lt_variance else 0.0
    var_over_lt = p.lead_time_mean * var_d + (daily_demand ** 2) * lt_var
    return z * math.sqrt(var_over_lt)


def reorder_point(p: Product, daily_demand: float, service: float, cv: float = 0.35,
                  account_for_lt_variance: bool = True) -> float:
    return daily_demand * p.lead_time_mean + safety_stock(
        p, daily_demand, service, cv, account_for_lt_variance)


def order_quantity(p: Product, daily_demand: float) -> float:
    """Economic order quantity, with a fixed ordering cost assumption."""
    order_cost = 120.0
    holding_per_unit_year = p.unit_cost * p.holding_cost_rate
    annual = max(1.0, daily_demand * 365)
    return math.sqrt(2 * annual * order_cost / max(0.01, holding_per_unit_year))


def simulate(p: Product, policy: Policy, days: int = 365, seed: int = 7,
             cv: float = 0.35, lead_time_sd: float = None,
             lead_time_mean: float = None,
             account_for_lt_variance: bool = True) -> Outcome:
    """Run one product for `days`. Overrides let a scenario change the supplier."""
    rnd = random.Random(seed)
    lt_mean = p.lead_time_mean if lead_time_mean is None else lead_time_mean
    lt_sd = p.lead_time_sd if lead_time_sd is None else lead_time_sd
    # a scenario may change lead time, so the policy must be computed from the
    # lead time actually in force -- not from the product's defaults
    planning = Product(**{**p.__dict__, "lead_time_mean": lt_mean, "lead_time_sd": lt_sd})

    baseline_daily = expected_demand(p, policy.price, policy.daily_ad_spend)
    rop = reorder_point(planning, baseline_daily, policy.target_service, cv,
                        account_for_lt_variance)
    eoq = max(1.0, order_quantity(planning, baseline_daily))

    on_hand = rop + eoq / 2          # start mid-cycle rather than empty
    pipeline = []                    # (arrival_day, quantity)
    out = Outcome(days=days)

    for day in range(days):
        for arrival, qty in [x for x in pipeline if x[0] == day]:
            on_hand += qty
        pipeline = [x for x in pipeline if x[0] > day]

        mean = expected_demand(p, policy.price, policy.daily_ad_spend,
                               seasonality_factor(day))
        demand = max(0, int(round(rnd.gauss(mean, demand_sd(mean, cv)))))

        sold = min(demand, int(on_hand))
        lost = demand - sold
        on_hand -= sold

        out.units_sold += sold
        out.units_lost += lost
        out.revenue += sold * policy.price
        out.cogs += sold * p.unit_cost
        out.ad_spend += policy.daily_ad_spend
        out.holding_cost += on_hand * p.unit_cost * p.holding_cost_rate / 365.0
        out.inventory_days += on_hand
        if lost > 0:
            out.stockout_days += 1

        inbound = sum(q for _, q in pipeline)
        if day % policy.review_days == 0 and on_hand + inbound <= rop:
            lt = max(1, int(round(rnd.gauss(lt_mean, lt_sd))))
            pipeline.append((day + lt, eoq))
            out.orders_placed += 1

    return out
