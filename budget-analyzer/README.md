# Budget Analyzer

Drop a bank-export CSV, get a savings rate. Transactions are categorized by merchant keyword, then summarized into KPIs, a category breakdown, and month-by-month cash flow — entirely in the browser, so no financial data leaves the page.

**[▶ Open the analyzer](https://abenezer0101.github.io/projects/budget-analyzer/)**

```bash
python3 generate_data.py    # regenerate the synthetic sample (seeded)
python3 analyze.py          # reference implementation / ground truth
```

## What it does

Input is any CSV with `date,description,amount` columns — positive amounts are income, negative are spending. Output:

- **KPIs:** total income, total spending, net saved, savings rate
- **Spending by category**, ranked
- **Monthly income vs. spending**
- **Savings rate by month**, with best and weakest months called out
- Table view for every chart, and a count of anything it failed to categorize

## Findings on the sample year

| Metric | Value |
|---|---|
| Transactions | 461 (0 uncategorized) |
| Income | $57,600.00 |
| Spending | $38,151.39 |
| Net saved | $19,448.61 |
| **Savings rate** | **33.76%** |

Housing alone is **45.6% of all spending** ($17,400) — more than the next four categories combined. Groceries follow at 16.5%. The discretionary lines people usually blame — Dining (3.7%) and Entertainment (1.9%) — are rounding errors against rent. Savings rate ranges from 27.3% in July to 39.1% in December; the July dip tracks a $400 flight, which is the point of charting the rate monthly rather than quoting one annual figure.

## Chart decisions

- **Category spending uses a single hue, not a rainbow.** It is one measure (dollars) across categories; colour would encode nothing. Rank order carries the meaning.
- **Income vs. spending shares one axis** — both are dollars, so a shared scale is honest.
- **Savings rate gets its own chart.** It is a percentage. Putting it on the dollar axis would be the dual-axis trick that lets two unrelated series appear to move together.
- Two-series palette validated for colour-vision deficiency: worst pair ΔE 24.7 (light) / 26.8 (dark), well clear of the ≥8 target.

## Verification: two implementations, compared

The risk in a browser analyzer is silent arithmetic drift — a number that looks plausible and is wrong. So the analysis exists twice: `analyze.py` (reference) and the JS in the page, with identical categorization rules. Both were run against the same 461 transactions and compared field by field:

```
MATCH  transactions   js=461       py=461
MATCH  uncategorized  js=0         py=0
MATCH  income         js=57600     py=57600.0
MATCH  expense        js=38151.39  py=38151.39
MATCH  net            js=19448.61  py=19448.61
MATCH  savings_rate   js=33.76     py=33.76
MATCH  all 11 categories
```

Also verified in headless Chromium: 3 charts, the category chart uses exactly **1** colour, the monthly chart has 2 named series, and the savings-rate chart has a single y-axis. No page errors.

> **A real bug this caught.** The page originally loaded its sample with `fetch()`, which browsers block on `file://` URLs. Served over GitHub Pages it worked; opened by double-clicking `index.html` after a clone, it silently rendered nothing. The sample is now emitted as `data/sample.js` and loaded via a `<script>` tag — which `file://` permits — from the same generator that writes the CSV, so the two cannot drift.

## Files

| File | Purpose |
|---|---|
| `index.html` | The analyzer — CSV parser, categorizer, charts |
| `analyze.py` | Reference implementation used to verify the JS |
| `generate_data.py` | Seeded synthetic sample → `transactions.csv` + `sample.js` |
| `data/transactions.csv` | 461 transactions across 2026 |

The CSV parser is hand-written (~15 lines, handles quoted fields) rather than pulled from a CDN — one less dependency for a page that handles financial data.

Sample data is synthetic. Merchants and amounts are plausible for an Atlanta-area budget but entirely generated.

## Skills

Client-side CSV parsing, rule-based categorization, KPI derivation, cross-implementation verification, chart-form selection, CVD-safe palettes, file:// vs http:// loading constraints.
