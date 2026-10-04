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
Total project-level shortfall across the fleet: 445 units
Of that, units sitting idle in another project's segregated stock
for the identical part: 445 units (100%)

  P-1012 (Pitot tube): A-CHECK-N226FY-2310 is short 20 units, while
  D-CHECK-N789TD-2309 holds 24 unused -> 20 units stranded
  P-1010 (Seat track fitting): D-CHECK-N671VP-2307 is short 18 units,
  while D-CHECK-N558BC-2305 holds 34 unused -> 18 units stranded
```

Every unit of shortfall in this run could have been covered by surplus
sitting idle under a *different* project for the *same part number* — stock
that project segregation makes legally and physically unreachable. A
plant-level inventory report would show the fleet comfortably stocked on
`P-1012`; the hangar working `N226FY` would still be waiting on a pitot
tube.

This isn't a rigged scenario — it's generic to the model. Once receipts are
bucketed per project and consumption is anything less than immediate and
exhaustive, idle pockets and concurrent shortfalls on the same part number
are close to inevitable whenever you run more than a handful of projects in
parallel. `analysis.py` computes it directly from the ledger: no manual
matching of which project is short against which project is sitting on
spares.

Two secondary KPIs come out of the same data for free: on-time delivery
rate by supplier (worst in this run: 18%), and average order→delivery lead
time by part criticality (AOG parts arrive faster than routine ones here —
20.1 vs 23.8 days — because urgency gets chased harder, not because AOG
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
python3 -m unittest tests -v   # 8 tests: schema integrity + pinned finding numbers
```

`tests.py` seeds an in-memory database independently of `airline_dn.db`,
checks referential integrity, confirms the generator is deterministic, and
pins the headline numbers above — so a change to the model that moves the
finding gets caught as a test failure, not reported as a new result.
