# Airline Supply Chain: Project-Specific DN Procurement

MySQL/SAP-style MRO procurement doesn't use a plant-wide parts pool. Stock
bought against a maintenance project — a C-check on one tail number, an
engine swap on another — is earmarked (account-assignment category `Q`) to
that project alone. A delivery note (DN) posts receipts into that project's
own segregated bucket; nothing else can draw from it, even another project
holding the identical part number.

That rule is the entire schema. Everything else — suppliers, purchase
orders, DNs, consumption — is ordinary procurement plumbing built around it.

## The finding

Simulating 15 projects, 8 suppliers, 20 part numbers, and a full
order → deliver → consume cycle (fixed seed, zero hand-tuning):

```
Total project-level shortfall across the fleet: 509 units
Of that, units sitting idle in another project's segregated stock
for the identical part: 495 units (97%)

  P-1010 (Seat track fitting): A-CHECK-N140RM-2306 is short 21 units,
  while D-CHECK-N558BC-2305 holds 40 unused -> 21 units stranded
  P-1009 (Oxygen generator, pax): C-CHECK-N804AX-2301 is short 18 units,
  while A-CHECK-N303GH-2308 holds 19 unused -> 18 units stranded
```

97% of the shortfall in this run could have been covered by surplus sitting
idle under a *different* project for the *same part number* — stock that
project segregation makes legally and physically unreachable. A plant-level
inventory report would show the fleet comfortably stocked on `P-1010`; the
hangar working `N140RM` would still be waiting on a seat track fitting.
(`stranded_coverage()` in `analysis.py` is a greedy match: each unit of idle
surplus is credited to at most one shortage, so this figure can't double-count
a surplus pool across several shortages.)

This isn't a rigged scenario — it's generic to the model. Once receipts are
bucketed per project and consumption is anything less than immediate and
exhaustive, idle pockets and concurrent shortfalls on the same part number
are close to inevitable whenever you run more than a handful of projects in
parallel. `analysis.py` computes it directly from the ledger: no manual
matching of which project is short against which project is sitting on
spares.

Two secondary KPIs come out of the same data for free: on-time delivery
rate by supplier (worst in this run: 31%), and average order→delivery lead
time by part criticality (AOG parts arrive faster than routine ones here —
20.8 vs 21.5 days — because urgency gets chased harder, not because AOG
parts ship faster by default).

## Schema

`sql/schema.sql` — SQLite, 8 tables:

- `suppliers`, `parts` (with `criticality`: `AOG` or `ROUTINE`), `projects`
- `purchase_orders` / `po_lines` — every line carries the owning `project_id`
- `delivery_notes` / `dn_lines` — `qty_delivered = qty_accepted + qty_rejected`
- `project_stock_issues` — consumption, scoped to `(project_id, part_id)`

A project's position on a part is purely:

```
shortfall    = SUM(qty_ordered) - SUM(qty_accepted)        -- unmet need
idle_surplus = SUM(qty_accepted) - SUM(qty_issued)          -- received, unconsumed
```

both clamped at zero — see the `PROJECT_PART_POSITION` query in
`analysis.py`.

## Run it

Zero dependencies, stdlib only (Python 3.11+):

```bash
python3 seed.py        # builds airline_dn.db from the schema, fixed seed
python3 analysis.py    # prints the finding + supplier/lead-time KPIs
python3 -m unittest tests -v   # 10 tests: schema integrity, date validity, pinned finding numbers
```

`tests.py` seeds an in-memory database independently of `airline_dn.db`,
checks referential integrity, confirms the generator is deterministic, and
pins the headline numbers above — so a change to the model that moves the
finding gets caught as a test failure, not reported as a new result.
