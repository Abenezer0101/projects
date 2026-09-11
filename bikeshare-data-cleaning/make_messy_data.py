"""Generate a realistically messy bike-share export.

Every defect here is one that shows up in real trip data:
inconsistent date formats, clock-skew negative durations, undocked-bike
outliers, duplicate ride IDs, station-name casing drift, missing user
types, and whitespace. Seeded, so the mess is reproducible.
"""
import csv, random, datetime, pathlib

random.seed(20260911)
OUT = pathlib.Path(__file__).parent / "data" / "trips_raw.csv"

# Station demand in real systems is heavily skewed -- a few hubs carry most
# trips. Sampling uniformly would flatten the chart into a non-finding.
STATIONS = ["Midtown MARTA", "Ponce City Market", "Georgia State University",
            "Centennial Olympic Park", "Atlantic Station", "Piedmont Park",
            "Krog Street Market", "Little Five Points", "Grant Park", "West End"]
STATION_WEIGHTS = [26, 21, 16, 12, 8, 6, 4, 3, 2, 2]
USERS = ["member", "casual"]

def jitter_station(name):
    """Real exports drift: casing, whitespace, and abbreviations."""
    r = random.random()
    if r < 0.08: return name.upper()
    if r < 0.14: return name.lower()
    if r < 0.20: return "  " + name + " "
    if r < 0.24: return name.replace("Street", "St.").replace("Park", "Pk")
    return name

def fmt_date(dt, style):
    return [dt.strftime("%Y-%m-%d %H:%M:%S"),
            dt.strftime("%m/%d/%Y %H:%M"),
            dt.strftime("%d-%b-%Y %H:%M")][style]

rows, ride_id = [], 100000
base = datetime.datetime(2026, 6, 1, 0, 0)

for day in range(60):
    weekend_day = (base + datetime.timedelta(days=day)).weekday() >= 5
    for _ in range(random.randint(70, 130)):
        ride_id += 1
        # Weekdays are commute-shaped (twin 8am/5pm peaks); weekends are
        # leisure-shaped (one broad midday hump). Using one distribution for
        # both would manufacture a weekend commute peak that does not exist.
        is_weekend = (base + datetime.timedelta(days=day)).weekday() >= 5
        hour = random.choices(range(24), weights=(
            [1,1,1,1,1,2,4,7,9,8,9,11,12,12,11,10,9,8,6,4,3,2,2,1] if is_weekend
            else [1,1,1,1,2,4,9,16,20,10,6,7,8,7,6,8,14,19,15,9,6,4,2,1]))[0]
        start = base + datetime.timedelta(days=day, hours=hour,
                                          minutes=random.randint(0, 59))
        member = random.random() < (0.45 if weekend_day else 0.75)  # weekends skew casual
        # members ride short and direct; casual riders wander
        mins = random.gauss(11, 4) if member else random.gauss(23, 11)
        mins = max(1.0, mins)
        a = random.choices(STATIONS, weights=STATION_WEIGHTS)[0]
        b = a
        while b == a:
            b = random.choices(STATIONS, weights=STATION_WEIGHTS)[0]
        row = {
            "ride_id": f"R{ride_id}",
            "started_at": fmt_date(start, random.choices([0,1,2],[0.7,0.2,0.1])[0]),
            "ended_at":   fmt_date(start + datetime.timedelta(minutes=mins),
                                   random.choices([0,1,2],[0.7,0.2,0.1])[0]),
            "start_station": jitter_station(a),
            "end_station":   jitter_station(b),
            "user_type": random.choice(USERS) if member is None else ("member" if member else "casual"),
        }
        # ---- injected defects ----
        r = random.random()
        if r < 0.012:                      # undocked bike: absurd duration
            row["ended_at"] = fmt_date(start + datetime.timedelta(days=random.randint(3, 21)), 0)
        elif r < 0.020:                    # clock skew: negative duration
            row["ended_at"] = fmt_date(start - datetime.timedelta(minutes=random.randint(1, 9)), 0)
        elif r < 0.030:                    # missing end station
            row["end_station"] = ""
        elif r < 0.042:                    # missing user type
            row["user_type"] = ""
        elif r < 0.050:                    # zero-length "rebalancing" trip
            row["ended_at"] = row["started_at"]
            row["end_station"] = row["start_station"]
        rows.append(row)

# duplicate ride IDs — the same ride exported twice
for dup in random.sample(rows, 45):
    rows.append(dict(dup))

random.shuffle(rows)
OUT.parent.mkdir(exist_ok=True)
with OUT.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print(f"wrote {len(rows):,} rows -> {OUT.name}")
