"""Reference amortization + invest-vs-prepay analysis.

The workbook computes all of this with live Excel formulas; this module is
the independent check on those numbers.

Run: python3 amortize.py [--json]
"""
import json, sys

PRINCIPAL   = 320_000.00
ANNUAL_RATE = 0.065
YEARS       = 30
EXTRA       = 200.00      # additional principal per month
INVEST_RATE = 0.070       # annual return if the extra were invested instead

def payment(principal, annual_rate, years):
    r = annual_rate / 12; n = years * 12
    return principal * r / (1 - (1 + r) ** -n)

def schedule(principal, annual_rate, years, extra=0.0):
    """Returns rows of (month, interest, principal_paid, balance)."""
    r = annual_rate / 12
    pmt = payment(principal, annual_rate, years)
    bal = principal
    rows = []
    m = 0
    while bal > 0.005 and m < years * 12 + 600:
        m += 1
        interest = bal * r
        princ = pmt - interest + extra
        if princ > bal:                 # final payment: don't overshoot
            princ = bal
        bal -= princ
        rows.append((m, interest, princ, max(bal, 0.0)))
    return pmt, rows

def future_value(monthly, annual_rate, months):
    """FV of an ordinary annuity — the extra invested instead of prepaid."""
    r = annual_rate / 12
    return monthly * (((1 + r) ** months - 1) / r)

def analyze():
    pmt, base = schedule(PRINCIPAL, ANNUAL_RATE, YEARS)
    _, fast   = schedule(PRINCIPAL, ANNUAL_RATE, YEARS, EXTRA)

    base_int = sum(r[1] for r in base)
    fast_int = sum(r[1] for r in fast)
    saved    = base_int - fast_int
    months_saved = len(base) - len(fast)

    # Both paths spend the SAME amount each month (pmt + EXTRA) and are valued
    # at the same horizon, month 360. That equal footing is the whole point --
    # comparing unequal cash flows is how this analysis is usually botched.
    #
    #   Invest path: pay only pmt for all 360 months (the loan never ends
    #                early), invest EXTRA every month for 360 months.
    #   Prepay path: pay pmt + EXTRA until the loan dies at `fast_months`,
    #                then invest the freed-up pmt + EXTRA for the remainder.
    invest_total = future_value(EXTRA, INVEST_RATE, YEARS * 12)
    prepay_total = future_value(pmt + EXTRA, INVEST_RATE, months_saved)

    return {
        "principal": PRINCIPAL, "rate": ANNUAL_RATE, "years": YEARS,
        "monthly_payment": round(pmt, 2),
        "base_months": len(base), "base_interest": round(base_int, 2),
        "base_total_paid": round(PRINCIPAL + base_int, 2),
        "extra": EXTRA,
        "fast_months": len(fast), "fast_interest": round(fast_int, 2),
        "interest_saved": round(saved, 2),
        "months_saved": months_saved,
        "years_saved": round(months_saved / 12, 1),
        "invest_rate": INVEST_RATE,
        "invest_path_value": round(invest_total, 2),
        "prepay_path_value": round(prepay_total, 2),
        "difference": round(invest_total - prepay_total, 2),
        "first_payment_interest_share": round(100 * base[0][1] / pmt, 1),
        "crossover_month": next(m for m, i, p, b in base if p > i),
    }

if __name__ == "__main__":
    a = analyze()
    if "--json" in sys.argv:
        print(json.dumps(a)); raise SystemExit
    print(f"${a['principal']:,.0f} at {a['rate']*100:.2f}% for {a['years']} years")
    print(f"  monthly payment          ${a['monthly_payment']:,.2f}")
    print(f"  total interest           ${a['base_interest']:,.2f}")
    print(f"  total paid               ${a['base_total_paid']:,.2f}")
    print(f"  first payment is {a['first_payment_interest_share']}% interest")
    print(f"  principal exceeds interest at month {a['crossover_month']}"
          f" (year {a['crossover_month']//12 + 1})")
    print(f"\nWith ${a['extra']:.0f}/month extra principal")
    print(f"  paid off in              {a['fast_months']} months"
          f"  ({a['years_saved']} years early)")
    print(f"  interest saved           ${a['interest_saved']:,.2f}")
    print(f"\nPrepay vs invest at {a['invest_rate']*100:.1f}%  (value at month 360)")
    print(f"  invest the extra         ${a['invest_path_value']:,.2f}")
    print(f"  prepay, then invest      ${a['prepay_path_value']:,.2f}")
    print(f"  difference               ${a['difference']:,.2f}")
