# Loan Amortization & ROI Model

A five-sheet Excel model for a $320,000 mortgage at 6.5% over 30 years. Every derived figure is a **live formula** — change an input on the Assumptions sheet and all 360 schedule rows, both payoff scenarios, and the ROI comparison recalculate.

**Deliverable:** [`loan_roi_model.xlsx`](./loan_roi_model.xlsx)

```bash
python3 amortize.py         # reference analysis
python3 build_workbook.py   # regenerate the workbook
```

## Sheets

| Sheet | Contents |
|---|---|
| **Assumptions** | Five yellow input cells + derived payment via `=PMT()` |
| **Summary** | Side-by-side results, both scenarios, and the prepay-vs-invest verdict |
| **Amortization** | 360 rows: opening balance, payment, interest, principal, closing, cumulative interest |
| **With Extra Payment** | The same schedule plus $200/month of extra principal |
| **Rate Sensitivity** | Payment and lifetime interest from 4.5% to 9.5% |

The schedule rows use `=IF(B<=0,0,…)` so the sheet goes quiet after payoff instead of producing negative balances, and the final payment is `MIN(payment, balance + interest)` so it settles the loan exactly rather than overshooting.

## Findings

**The first payment is 85.7% interest.** Principal does not exceed interest until **month 233** — year 20 of a 30-year loan. Total interest over the full term is **$408,142**, meaning $728,142 repaid on $320,000 borrowed.

**$200/month extra retires the loan 6.6 years early** (281 months instead of 360) and saves **$105,429** in interest.

**But prepaying is still the worse move here.** Compared on equal footing — the same monthly outflow, both valued at month 360:

| Path | Value at month 360 |
|---|---:|
| Pay the scheduled payment, invest $200/mo at 7% | **$243,994** |
| Pay $200/mo extra, then invest the freed-up payment | $222,239 |
| **Advantage of investing** | **$21,755** |

A 0.5-point spread between the investment return and the loan rate compounds into roughly $22k over thirty years. The caveat that belongs with it: 7% is a *risky expected* return while 6.5% is a *guaranteed* one, so this is not a like-for-like comparison — it is a risk-tolerance decision, not arithmetic.

> **A modelling error I caught and fixed.** My first version had investing ahead by $141,477 — an implausible margin that should not survive a sanity check, and didn't. I had credited the invest path with the freed-up mortgage payment after month 281, but in that path *you are still paying the mortgage* through month 360; nothing is freed up. Comparing two paths with different cash outflows is the standard way this analysis gets botched. The corrected model holds monthly outflow identical in both paths, which is what makes the $21,755 meaningful.

## Verification

`amortize.py` computes the analysis independently in Python. Because openpyxl writes formulas without evaluating them, the workbook's formulas were verified by **replaying their exact semantics** (`C = IF(B<=0,0,MIN(pay,B+D))`, `D = B*r/12`, `E = C-D`, `F = B-E`) and comparing:

```
MATCH  standard months      formulas=360           reference=360
MATCH  standard interest    formulas=408,142.36    reference=408,142.36
MATCH  extra months         formulas=281           reference=281
MATCH  extra interest       formulas=302,713.69    reference=302,713.69
MATCH  invest path          formulas=$243,994.20   reference=$243,994.20
MATCH  prepay path          formulas=$222,238.91   reference=$222,238.91
```

All formula sheet references resolve (0 broken).

**Not verified:** the workbook was never opened by a real spreadsheet engine. LibreOffice is installed in this environment but fails to load even a trivial openpyxl file, so recalculation could not be confirmed here. The formula *logic* is verified above; the formula *syntax* should be confirmed on first open in Excel.

## Skills

`PMT` / `FV` financial functions, amortization recurrences, guard conditions for terminal rows, sensitivity tables, opportunity-cost modelling with equal cash flows, separating guaranteed from expected returns.
