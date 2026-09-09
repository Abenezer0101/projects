"""Generate a year of plausible transactions. Seeded -> reproducible."""
import csv, json, random, datetime, pathlib

random.seed(20260909)
OUT = pathlib.Path(__file__).parent / "data" / "transactions.csv"

# (merchant, category, low, high, times per month)
RECURRING = [
    ("Paycheck - Acme Corp", "Income",        2400, 2400, 2),
    ("Sunrise Apartments",   "Housing",      -1450, -1450, 1),
    ("Georgia Power",        "Utilities",      -95,  -160, 1),
    ("Xfinity Internet",     "Utilities",      -70,   -70, 1),
    ("T-Mobile",             "Utilities",      -55,   -55, 1),
    ("Planet Fitness",       "Health",         -25,   -25, 1),
    ("Spotify",              "Subscriptions",  -12,   -12, 1),
    ("Netflix",              "Subscriptions",  -16,   -16, 1),
    ("State Farm Insurance", "Insurance",     -110,  -110, 1),
    ("MARTA Breeze",         "Transport",      -95,   -95, 1),
]
VARIABLE = [
    ("Kroger",            "Groceries",     -35,  -140, 5),
    ("Publix",            "Groceries",     -25,   -95, 2),
    ("Chipotle",          "Dining",        -11,   -19, 3),
    ("Starbucks",         "Dining",         -5,   -12, 5),
    ("Waffle House",      "Dining",         -9,   -22, 2),
    ("Shell",             "Transport",     -30,   -55, 2),
    ("Amazon",            "Shopping",      -15,  -120, 3),
    ("Target",            "Shopping",      -20,   -90, 2),
    ("CVS Pharmacy",      "Health",        -8,    -45, 1),
    ("AMC Theatres",      "Entertainment", -14,   -32, 1),
    ("Steam",             "Entertainment", -10,   -60, 1),
]

rows = []
for m in range(1, 13):
    days = (datetime.date(2026, m % 12 + 1, 1) - datetime.timedelta(days=1)).day if m < 12 else 31
    for merchant, cat, lo, hi, n in RECURRING + VARIABLE:
        for _ in range(n):
            day = random.randint(1, days)
            amt = lo if lo == hi else round(random.uniform(min(lo, hi), max(lo, hi)), 2)
            rows.append((f"2026-{m:02d}-{day:02d}", merchant, f"{amt:.2f}"))
    # occasional irregular expenses
    if m in (3, 7, 11):
        rows.append((f"2026-{m:02d}-{random.randint(1,28):02d}", "Delta Air Lines", f"{-random.randint(220,480)}.00"))
    if m in (5, 9):
        rows.append((f"2026-{m:02d}-{random.randint(1,28):02d}", "Emory Clinic", f"{-random.randint(120,340)}.00"))

rows.sort()
OUT.parent.mkdir(exist_ok=True)
with OUT.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "description", "amount"])
    w.writerows(rows)
# Also emit a JS fallback: browsers block fetch() on file:// URLs, so a
# script tag is the only way the sample loads when the page is opened
# directly from disk rather than served over http.
csv_text = "date,description,amount\n" + "\n".join(",".join(r) for r in rows) + "\n"
JS = OUT.parent / "sample.js"
JS.write_text("window.SAMPLE_CSV = " + json.dumps(csv_text) + ";\n")
print(f"wrote {len(rows)} transactions -> {OUT.name} and {JS.name}")
