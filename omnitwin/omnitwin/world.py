"""The enterprise being simulated: products, demand, and the levers on it.

A digital twin is only as honest as its mechanics. Everything here is an
explicit, stated equation rather than a fitted black box, so a reader can
disagree with the model instead of having to trust it.

The parameters below are PLANTED. That matters for how the tests read: when
`estimate.py` recovers an elasticity of -1.8 from generated history, that
proves the estimator works, not that -1.8 is true of any real company. See the
README -- fitting a model to data you generated and calling the fit a finding
is circular, and it is the most common way simulation projects mislead.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    category: str
    base_price: float          # the reference price the elasticity is measured at
    unit_cost: float
    base_demand: float         # units per day at base price with no advertising
    elasticity: float          # d(log q)/d(log p). Negative. -1 is the knife edge.
    ad_saturation: float       # spend at which incremental response has half decayed
    ad_max_lift: float         # multiplier ceiling advertising can reach
    lead_time_mean: float      # days from order to receipt
    lead_time_sd: float        # variability in that, which matters more than the mean
    holding_cost_rate: float = 0.25    # annual, as a fraction of unit cost
    stockout_penalty: float = 0.5      # lost margin multiplier when a sale is missed

    @property
    def margin(self) -> float:
        return self.base_price - self.unit_cost


def demand_at_price(p: Product, price: float) -> float:
    """Constant-elasticity demand: q = q0 * (price / base_price) ** elasticity.

    The useful property, and the one most pricing intuition gets backwards: at
    elasticity > -1 a price rise grows revenue, at < -1 it shrinks it, and the
    profit-maximising price is a different number again because cost enters.
    """
    if price <= 0:
        raise ValueError("price must be positive")
    return p.base_demand * (price / p.base_price) ** p.elasticity


def ad_multiplier(p: Product, daily_spend: float) -> float:
    """Diminishing returns on advertising, as a Hill curve.

    Linear ad response is the single most damaging simplification in marketing
    models: it says the tenth million buys what the first did, so every
    optimiser it feeds recommends spending everything.
    """
    if daily_spend < 0:
        raise ValueError("ad spend cannot be negative")
    if daily_spend == 0:
        return 1.0
    lift = (p.ad_max_lift - 1.0) * daily_spend / (p.ad_saturation + daily_spend)
    return 1.0 + lift


def expected_demand(p: Product, price: float, daily_ad_spend: float,
                    seasonality: float = 1.0) -> float:
    return demand_at_price(p, price) * ad_multiplier(p, daily_ad_spend) * seasonality


def seasonality_factor(day: int, amplitude: float = 0.18) -> float:
    """A yearly cycle plus a weekly one. Retail has both."""
    yearly = 1.0 + amplitude * math.sin(2 * math.pi * (day - 80) / 365.0)
    weekly = 1.0 + 0.12 * math.sin(2 * math.pi * (day % 7) / 7.0)
    return yearly * weekly


CATALOGUE = [
    Product("SKU-1001", "Trail Runner 2", "Footwear", base_price=120.0, unit_cost=48.0,
            base_demand=140, elasticity=-1.8, ad_saturation=900, ad_max_lift=1.45,
            lead_time_mean=21, lead_time_sd=6),
    Product("SKU-1002", "Alpine Shell", "Outerwear", base_price=260.0, unit_cost=104.0,
            base_demand=45, elasticity=-1.3, ad_saturation=700, ad_max_lift=1.35,
            lead_time_mean=34, lead_time_sd=11),
    Product("SKU-1003", "Base Layer Tee", "Apparel", base_price=38.0, unit_cost=11.0,
            base_demand=390, elasticity=-2.4, ad_saturation=1200, ad_max_lift=1.60,
            lead_time_mean=14, lead_time_sd=3),
    Product("SKU-1004", "Summit Pack 40L", "Equipment", base_price=185.0, unit_cost=76.0,
            base_demand=62, elasticity=-0.9, ad_saturation=500, ad_max_lift=1.25,
            lead_time_mean=28, lead_time_sd=9),
    Product("SKU-1005", "Merino Socks", "Apparel", base_price=22.0, unit_cost=6.5,
            base_demand=520, elasticity=-2.9, ad_saturation=1500, ad_max_lift=1.70,
            lead_time_mean=12, lead_time_sd=2),
    Product("SKU-1006", "Storm Gloves", "Accessories", base_price=54.0, unit_cost=19.0,
            base_demand=110, elasticity=-1.6, ad_saturation=600, ad_max_lift=1.40,
            lead_time_mean=25, lead_time_sd=8),
]


def catalogue() -> list:
    return list(CATALOGUE)


def by_sku(sku: str) -> Product:
    for p in CATALOGUE:
        if p.sku == sku:
            return p
    raise KeyError(sku)
