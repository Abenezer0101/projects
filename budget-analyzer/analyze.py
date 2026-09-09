"""Reference implementation of the budget analysis.

The browser app reimplements these exact rules in JS; this file is the
ground truth the JS output is checked against.

Run:  python3 analyze.py
"""
import csv, pathlib, collections, json, sys

# merchant keyword -> category. First match wins, so order matters.
RULES = [
    ("paycheck",   "Income"),        ("apartments", "Housing"),
    ("power",      "Utilities"),     ("xfinity",    "Utilities"),
    ("t-mobile",   "Utilities"),     ("fitness",    "Health"),
    ("cvs",        "Health"),        ("clinic",     "Health"),
    ("spotify",    "Subscriptions"), ("netflix",    "Subscriptions"),
    ("insurance",  "Insurance"),     ("marta",      "Transport"),
    ("shell",      "Transport"),     ("delta",      "Travel"),
    ("kroger",     "Groceries"),     ("publix",     "Groceries"),
    ("chipotle",   "Dining"),        ("starbucks",  "Dining"),
    ("waffle",     "Dining"),        ("amazon",     "Shopping"),
    ("target",     "Shopping"),      ("amc",        "Entertainment"),
    ("steam",      "Entertainment"),
]

def categorize(desc):
    d = desc.lower()
    for kw, cat in RULES:
        if kw in d:
            return cat
    return "Uncategorized"

def analyze(path):
    income = expense = 0.0
    by_cat = collections.defaultdict(float)
    by_month = collections.defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    uncategorized = 0
    rows = list(csv.DictReader(open(path)))
    for r in rows:
        amt = float(r["amount"])
        cat = categorize(r["description"])
        month = r["date"][:7]
        if cat == "Uncategorized":
            uncategorized += 1
        if amt > 0:
            income += amt
            by_month[month]["income"] += amt
        else:
            expense += -amt
            by_cat[cat] += -amt
            by_month[month]["expense"] += -amt
    net = income - expense
    return {
        "transactions": len(rows),
        "uncategorized": uncategorized,
        "income": round(income, 2),
        "expense": round(expense, 2),
        "net": round(net, 2),
        "savings_rate": round(100 * net / income, 2) if income else 0.0,
        "by_category": {k: round(v, 2) for k, v in sorted(by_cat.items(), key=lambda x: -x[1])},
        "by_month": {m: {"income": round(v["income"], 2),
                         "expense": round(v["expense"], 2),
                         "rate": round(100*(v["income"]-v["expense"])/v["income"], 2) if v["income"] else 0}
                     for m, v in sorted(by_month.items())},
    }

if __name__ == "__main__":
    p = pathlib.Path(__file__).parent / "data" / "transactions.csv"
    r = analyze(p)
    if "--json" in sys.argv:
        print(json.dumps(r)); raise SystemExit
    print(f"{r['transactions']} transactions, {r['uncategorized']} uncategorized")
    print(f"Income   ${r['income']:>10,.2f}")
    print(f"Expenses ${r['expense']:>10,.2f}")
    print(f"Net      ${r['net']:>10,.2f}   savings rate {r['savings_rate']}%")
    print("\nTop spending categories")
    for k, v in list(r["by_category"].items())[:6]:
        print(f"  {k:<14} ${v:>9,.2f}  {100*v/r['expense']:5.1f}% of spend")
    rates = [(m, v["rate"]) for m, v in r["by_month"].items()]
    best = max(rates, key=lambda x: x[1]); worst = min(rates, key=lambda x: x[1])
    print(f"\nBest month  {best[0]}  {best[1]}%")
    print(f"Worst month {worst[0]}  {worst[1]}%")
