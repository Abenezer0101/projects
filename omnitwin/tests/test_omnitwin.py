"""python3 -m unittest discover -s tests   (stdlib only)

Two kinds of test here. Ordinary ones pin the mechanics. The others exist
because a simulator's dangerous failure is not a crash -- it is a plausible
number. Those check a result against a SECOND route to the same answer: a
closed-form price against a grid search, planted parameters against recovered
ones, a boundary solution against being reported as an optimum.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from omnitwin import scenario, sim, world
from omnitwin.sim import Policy, Z, reorder_point, safety_stock, simulate
from omnitwin.world import (Product, ad_multiplier, by_sku, catalogue,
                            demand_at_price, expected_demand, seasonality_factor)

P = by_sku("SKU-1001")


class TestDemand(unittest.TestCase):
    def test_base_price_returns_base_demand(self):
        self.assertAlmostEqual(demand_at_price(P, P.base_price), P.base_demand)

    def test_demand_falls_as_price_rises(self):
        q = [demand_at_price(P, x) for x in (80, 100, 120, 140, 160)]
        self.assertEqual(q, sorted(q, reverse=True))

    def test_elasticity_is_what_the_curve_actually_does(self):
        """A 1% price rise must move quantity by elasticity percent."""
        p0, p1 = 100.0, 101.0
        q0, q1 = demand_at_price(P, p0), demand_at_price(P, p1)
        measured = math.log(q1 / q0) / math.log(p1 / p0)
        self.assertAlmostEqual(measured, P.elasticity, places=2)

    def test_elastic_and_inelastic_split_at_minus_one(self):
        elastic = Product(**{**P.__dict__, "elasticity": -2.0})
        inelastic = Product(**{**P.__dict__, "elasticity": -0.5})
        rev = lambda pr, x: demand_at_price(pr, x) * x
        self.assertLess(rev(elastic, 132), rev(elastic, 120))      # rise loses revenue
        self.assertGreater(rev(inelastic, 132), rev(inelastic, 120))   # rise gains it

    def test_zero_or_negative_price_is_refused(self):
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                demand_at_price(P, bad)

    def test_advertising_has_diminishing_returns(self):
        """Each extra pound must buy less than the one before it."""
        steps = [ad_multiplier(P, s) for s in (0, 500, 1000, 1500, 2000, 2500)]
        gains = [b - a for a, b in zip(steps, steps[1:])]
        self.assertEqual(gains, sorted(gains, reverse=True), gains)
        self.assertTrue(all(g > 0 for g in gains))

    def test_advertising_cannot_exceed_its_ceiling(self):
        self.assertLess(ad_multiplier(P, 10 ** 9), P.ad_max_lift)
        self.assertAlmostEqual(ad_multiplier(P, 0), 1.0)

    def test_negative_ad_spend_is_refused(self):
        with self.assertRaises(ValueError):
            ad_multiplier(P, -1)

    def test_seasonality_averages_to_about_one(self):
        vals = [seasonality_factor(d) for d in range(365)]
        self.assertAlmostEqual(sum(vals) / len(vals), 1.0, places=1)
        self.assertGreater(max(vals), min(vals))


class TestSafetyStock(unittest.TestCase):
    def test_a_higher_service_target_needs_more_buffer(self):
        vals = [safety_stock(P, 140, s) for s in sorted(Z)]
        self.assertEqual(vals, sorted(vals))

    def test_fifty_percent_target_means_no_buffer(self):
        """Z[0.50] is 0.0, and `Z.get(s) or Z[0.95]` silently turned that
        legitimate zero into the 95% multiplier."""
        self.assertEqual(safety_stock(P, 140, 0.50), 0.0)
        self.assertGreater(safety_stock(P, 140, 0.95), 0.0)

    def test_an_unknown_target_is_refused_not_guessed(self):
        with self.assertRaises(ValueError):
            safety_stock(P, 140, 0.93)

    def test_lead_time_variance_enters_squared_by_demand(self):
        """The asymmetry the project is about, as an equality.

        var(D over LT) = E[LT]*var(D) + E[D]^2*var(LT)
        """
        d, cv, z = 140.0, 0.35, Z[0.95]
        expected = z * math.sqrt(P.lead_time_mean * (d * cv) ** 2
                                 + d ** 2 * P.lead_time_sd ** 2)
        self.assertAlmostEqual(safety_stock(P, d, 0.95, cv), expected, places=6)

    def test_ignoring_lead_time_variance_shrinks_the_buffer(self):
        aware = safety_stock(P, 140, 0.95, account_for_lt_variance=True)
        blind = safety_stock(P, 140, 0.95, account_for_lt_variance=False)
        self.assertGreater(aware, blind * 2)

    def test_a_reliable_supplier_needs_less_than_a_slow_one(self):
        slow = Product(**{**P.__dict__, "lead_time_mean": 42, "lead_time_sd": 2})
        erratic = Product(**{**P.__dict__, "lead_time_mean": 21, "lead_time_sd": 12})
        self.assertGreater(safety_stock(erratic, 140, 0.95),
                           safety_stock(slow, 140, 0.95))

    def test_reorder_point_covers_the_lead_time_plus_the_buffer(self):
        self.assertAlmostEqual(reorder_point(P, 140, 0.95),
                               140 * P.lead_time_mean + safety_stock(P, 140, 0.95))


class TestSimulation(unittest.TestCase):
    def setUp(self):
        self.pol = Policy(price=P.base_price, daily_ad_spend=400)

    def test_a_run_is_reproducible(self):
        a = simulate(P, self.pol, days=180, seed=3)
        b = simulate(P, self.pol, days=180, seed=3)
        self.assertEqual(a.as_dict(), b.as_dict())

    def test_different_seeds_give_different_runs(self):
        a = simulate(P, self.pol, days=180, seed=3)
        b = simulate(P, self.pol, days=180, seed=4)
        self.assertNotEqual(a.as_dict(), b.as_dict())

    def test_the_books_balance(self):
        o = simulate(P, self.pol, days=365, seed=1)
        self.assertAlmostEqual(o.revenue, o.units_sold * self.pol.price, places=4)
        self.assertAlmostEqual(o.cogs, o.units_sold * P.unit_cost, places=4)
        self.assertAlmostEqual(o.net_profit,
                               o.gross_profit - o.ad_spend - o.holding_cost, places=4)
        self.assertAlmostEqual(o.ad_spend, self.pol.daily_ad_spend * 365, places=4)

    def test_nothing_is_sold_from_an_empty_shelf(self):
        o = simulate(P, self.pol, days=90, seed=2)
        self.assertLessEqual(o.units_sold, o.units_sold + o.units_lost)
        self.assertGreaterEqual(o.units_lost, 0)
        self.assertGreaterEqual(o.avg_inventory, 0)

    def test_service_level_is_sold_over_demanded(self):
        o = simulate(P, self.pol, days=120, seed=5)
        self.assertAlmostEqual(o.service_level,
                               o.units_sold / (o.units_sold + o.units_lost))

    def test_a_higher_target_really_does_raise_achieved_service(self):
        low = [simulate(P, Policy(P.base_price, 400, target_service=0.80),
                        days=365, seed=s) for s in range(8)]
        high = [simulate(P, Policy(P.base_price, 400, target_service=0.99),
                         days=365, seed=s) for s in range(8)]
        self.assertGreater(sum(o.service_level for o in high),
                           sum(o.service_level for o in low))

    def test_a_blind_planner_loses_service_to_the_same_supplier(self):
        """The supplier is identical in both runs. Only the buffer differs."""
        aware = [simulate(P, self.pol, days=365, seed=s,
                          account_for_lt_variance=True) for s in range(10)]
        blind = [simulate(P, self.pol, days=365, seed=s,
                          account_for_lt_variance=False) for s in range(10)]
        a = sum(o.service_level for o in aware) / len(aware)
        b = sum(o.service_level for o in blind) / len(blind)
        self.assertGreater(a - b, 0.02, (a, b))

    def test_raising_the_price_sells_fewer_units(self):
        cheap = simulate(P, Policy(P.base_price * 0.9, 400), days=365, seed=1)
        dear = simulate(P, Policy(P.base_price * 1.1, 400), days=365, seed=1)
        self.assertGreater(cheap.units_sold, dear.units_sold)

    def test_advertising_sells_more_units(self):
        none = simulate(P, Policy(P.base_price, 0), days=365, seed=1)
        some = simulate(P, Policy(P.base_price, 1500), days=365, seed=1)
        self.assertGreater(some.units_sold, none.units_sold)

    def test_a_zero_day_run_does_not_divide_by_zero(self):
        o = simulate(P, self.pol, days=0, seed=1)
        self.assertEqual(o.units_sold, 0)
        self.assertEqual(o.avg_inventory, 0.0)
        self.assertEqual(o.service_level, 1.0)

    def test_a_scenario_lead_time_changes_the_policy_too(self):
        """Lengthening the lead time must move the reorder point, or the
        simulation is planning against a supplier it no longer has."""
        short = [simulate(P, self.pol, days=365, seed=s, lead_time_mean=7)
                 for s in range(6)]
        long = [simulate(P, self.pol, days=365, seed=s, lead_time_mean=60)
                for s in range(6)]
        self.assertGreater(sum(o.avg_inventory for o in long),
                           sum(o.avg_inventory for o in short))


class TestOptimum(unittest.TestCase):
    """The grid search and the textbook formula are two routes to one number."""

    def test_grid_agrees_with_the_closed_form_where_one_exists(self):
        for p in catalogue():
            cf = scenario.closed_form_price(p)
            if cf is None:
                continue
            price, _, status = scenario.optimal_price(p, ad_spend=0.0)
            step = p.base_price * (6.0 - 0.2) / 290
            self.assertEqual(status, "interior", p.name)
            self.assertLess(abs(price - cf), step, f"{p.name}: grid {price} vs closed {cf}")

    def test_inelastic_demand_is_reported_unbounded_not_optimal(self):
        """Elasticity > -1 has no finite profit-maximising price. Returning
        the grid's last rung as an 'optimum' would be a confident fiction."""
        stubborn = Product(**{**P.__dict__, "elasticity": -0.6})
        _, _, status = scenario.optimal_price(stubborn)
        self.assertEqual(status, "unbounded")
        self.assertIsNone(scenario.closed_form_price(stubborn))

    def test_optimal_ad_spend_is_interior_not_infinite(self):
        """Diminishing returns must produce a finite answer; linear response
        would send every optimiser to the ceiling."""
        spend, profit = scenario.optimal_ad_spend(P, lo=0.0, hi=20000.0, steps=201)
        self.assertGreater(spend, 0)
        self.assertLess(spend, 19000)

    def test_profit_at_the_optimum_beats_its_neighbours(self):
        price, profit, _ = scenario.optimal_price(P, ad_spend=0.0)
        for nudge in (0.9, 0.95, 1.05, 1.1):
            q = expected_demand(P, price * nudge, 0.0)
            self.assertLessEqual(q * (price * nudge - P.unit_cost), profit + 1e-6)


class TestScenario(unittest.TestCase):
    def test_no_change_means_no_difference(self):
        r = scenario.apply_scenario(products=[P], days=120, seeds=4)
        for k in ("revenue", "net_profit", "units_sold"):
            d = r["summary"][k]
            self.assertAlmostEqual(d.before, d.after, places=4, msg=k)

    def test_a_price_rise_moves_revenue_the_way_elasticity_says(self):
        r = scenario.apply_scenario(products=[P], days=365, seeds=6, price_change=0.10)
        self.assertLess(r["summary"]["units_sold"].after,
                        r["summary"]["units_sold"].before)
        # elasticity -1.8 is elastic, so a price rise must shrink revenue
        self.assertLess(r["summary"]["revenue"].after, r["summary"]["revenue"].before)

    def test_cutting_advertising_sells_less(self):
        r = scenario.apply_scenario(products=[P], days=365, seeds=6, ad_change=-0.5)
        self.assertLess(r["summary"]["units_sold"].after,
                        r["summary"]["units_sold"].before)

    def test_a_supply_shock_hurts_service(self):
        r = scenario.apply_scenario(products=[P], days=365, seeds=8,
                                    lead_time_add=30, lead_time_sd_mult=3.0,
                                    account_for_lt_variance=False)
        self.assertLess(r["summary"]["service_level"].after,
                        r["summary"]["service_level"].before)

    def test_every_product_appears_in_the_rows(self):
        r = scenario.apply_scenario(days=60, seeds=2)
        self.assertEqual(len(r["rows"]), len(catalogue()))

    def test_delta_percentage_handles_a_zero_baseline(self):
        self.assertIsNone(scenario.Delta("x", 0.0, 5.0).pct)
        self.assertAlmostEqual(scenario.Delta("x", 100.0, 110.0).pct, 0.10)


if __name__ == "__main__":
    unittest.main(verbosity=1)
