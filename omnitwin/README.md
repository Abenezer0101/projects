# omnitwin

Simulate the company before you change it.

A digital twin of a small retail business: six products with stated demand
mechanics, a stochastic inventory simulator, and a what-if layer that moves the
levers and reports the difference. No dependencies, Python 3.11+, stdlib only.

```bash
python3 -m omnitwin.cli whatif --price +5 --ads -20
python3 -m omnitwin.cli whatif --lead-time +14 --lead-time-sd x3 --blind
python3 -m omnitwin.cli optimise
python3 -m omnitwin.cli service
python3 -m unittest discover -s tests      # 37 tests
```

This is the simulator core — the part everything else in the OMNITWIN plan
rests on. No agents, no dashboard, no connectors yet. A war room of AI agents
arguing on top of a sound simulator is a product; on top of nothing it is a
demo that falls over the first time somebody checks a number.

## The honest caveat, first

**The parameters are planted.** Elasticities, ad-saturation points and lead
times are written into `world.py` by hand. Recovering them from generated
history would prove the estimator works — it would say nothing whatsoever
about any real company. Fitting a model to data you generated and calling the
fit a finding is circular, and it is the most common way simulation projects
mislead.

What *is* transferable is the mechanics: the equations are stated, and the
results below follow from them the way they would follow from any business
with a similar shape.

## Finding: the cost of planning with average lead time

Most inventory planning uses one lead-time number — the average. The supplier
is exactly as erratic either way; the buffer just stops covering it.

Safety stock has to cover demand across a replenishment lead time, and

```
var(demand over lead time) = E[LT] · var(D)  +  E[D]² · var(LT)
```

The second term carries **mean demand squared**. Variability therefore scales
with volume and length does not, which is why a fast-moving product with an
unreliable supplier is a much harder problem than a slow-moving one with a
distant supplier.

Same supplier, same demand, 25 runs each, 365 days — the only difference is
whether the planner's buffer accounts for `var(LT)`:

| Product | Lead time | Service, aware | Service, blind | Profit lost / yr |
| --- | --- | --- | --- | --- |
| Trail Runner 2 | 21 ± 6 | 99.35% | 92.57% | −£268,905 |
| Alpine Shell | 34 ± 11 | 99.47% | 91.08% | −£219,900 |
| Base Layer Tee | 14 ± 3 | 98.62% | 94.22% | −£191,425 |
| Summit Pack 40L | 28 ± 9 | 99.29% | 90.09% | −£239,845 |
| Merino Socks | 12 ± 2 | 98.93% | 96.67% | −£71,153 |
| Storm Gloves | 25 ± 8 | 99.03% | 91.62% | −£114,424 |

The damage tracks the ratio of sd to mean, not either alone: Summit Pack
(28 ± 9) loses 9.2 points of service, Merino Socks (12 ± 2) loses 2.3.

## Finding: variance costs capital, not service — if the policy knows

I expected lead-time variability to wreck service levels. Measured, it barely
moves them. Adding 7 days to the *standard deviation* of a 21 ± 6 day lead
time **doubles safety stock** (1,430 → 3,017 units) and pushes average
inventory from 2,211 to 3,929 — while service goes *up*.

The policy is compensating. The bill arrives as working capital tied up in a
warehouse, not as unhappy customers. That is only true while the buffer is
computed from the lead time actually in force, which is precisely what the
table above shows happens when it is not.

## Finding: 95% service is a convention, not an optimum

For Trail Runner 2 a lost sale costs 6× what holding a unit for a year does.
Sweeping the target:

| Target | Achieved | Avg inventory | Units lost | Net profit |
| --- | --- | --- | --- | --- |
| 50% | 88.10% | 1,065 | 7,001 | £3,567,294 |
| 80% | 95.34% | 1,540 | 2,737 | £3,863,506 |
| 90% | 98.09% | 1,912 | 1,121 | £3,975,980 |
| 95% | 99.25% | 2,211 | 440 | £4,013,734 |
| 97.5% | 99.65% | 2,523 | 209 | £4,031,034 |
| **99%** | 99.91% | 2,865 | 55 | **£4,034,508** |

Profit is still climbing at 99%. Whenever margin dwarfs holding cost, the
default 95% target leaves money on the shelf — and the number that decides it
is the ratio of those two, which nobody has to guess at.

## Two bugs worth naming

**A falsy zero.** Safety stock read `z = Z.get(service) or Z[0.95]`. `Z[0.50]`
is `0.0`, which is falsy, so a legitimate zero-buffer target silently became
the 95% multiplier — and every 50% run reported 95% numbers. Found because the
sweep above printed two identical rows. It now raises on an unknown target
rather than guessing one.

**A grid returning its own edge.** `optimal_price` searched 0.5× to 2× the base
price. For Merino Socks the true profit-maximising price is £9.92, below that
range, so the search returned its lower bound of £11.00 and looked entirely
plausible. The grid is now wide, and it reports whether the winner sat on a
boundary instead of presenting a boundary as an answer.

## Where the model breaks, stated

Constant-elasticity demand with elasticity between −1 and 0 is **inelastic**:
a 1% price rise costs less than 1% of volume, so modelled profit climbs
without bound and there is no optimum. Summit Pack 40L (−0.9) is such a
product. `optimise` reports it as `unbounded` rather than printing whatever
price the grid stopped at.

This is a property of the functional form, not advice to raise prices forever.
Any real demand curve bends. The model does not, and pretending otherwise is
how a twin starts producing confident nonsense.

The grid search is cross-checked against the textbook monopoly price
`c · e / (e + 1)` wherever that exists — two independent routes to one number,
so a mistake in either shows up as a disagreement instead of a confident wrong
answer.

## Layout

```
omnitwin/world.py      products, demand, elasticity, ad response, seasonality
omnitwin/sim.py        day-by-day inventory simulation, safety stock, service
omnitwin/scenario.py   what-if deltas, price and ad-spend optima
omnitwin/cli.py        whatif / optimise / service / catalogue
tests/                 37 tests
```

Every figure in this README is produced by the code, and the ones that make a
claim are pinned by a test.
