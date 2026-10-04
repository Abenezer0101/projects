"""Deterministic synthetic data for the project-segregated procurement model.

Nothing here is hand-rigged to produce the headline finding in analysis.py.
The generator just plays out an ordinary MRO procurement cycle per project —
order, partial/late delivery, partial consumption — with a fixed seed. The
stranded-stock effect analysis.py reports falls out of the segregation rule
itself, not out of the random data.
"""
import random
import sqlite3
from pathlib import Path

SEED = 42
SCHEMA_PATH = Path(__file__).parent / "sql" / "schema.sql"

SUPPLIERS = [
    ("AeroParts Global", "US"), ("Transat Component Services", "CA"),
    ("Lufthansa Technik Logistik", "DE"), ("SR Technics Supply", "CH"),
    ("StandardAero Materiel", "US"), ("Satair", "DK"),
    ("AJW Group", "GB"), ("Pacific Avionics Trading", "SG"),
]

PART_CATALOG = [
    ("Hydraulic actuator, main gear", "AOG", 8400),
    ("Fuel pump, center tank", "AOG", 6200),
    ("Avionics LRU, FMS", "AOG", 15800),
    ("Brake assembly, main wheel", "AOG", 9100),
    ("Engine igniter plug", "ROUTINE", 420),
    ("Cabin air valve", "ROUTINE", 1850),
    ("Window heat controller", "AOG", 3200),
    ("Tire, nose wheel", "ROUTINE", 980),
    ("Oxygen generator, pax", "AOG", 540),
    ("Seat track fitting", "ROUTINE", 260),
    ("APU starter", "AOG", 11200),
    ("Pitot tube", "AOG", 2650),
    ("Galley water heater", "ROUTINE", 710),
    ("Wheel bearing kit", "ROUTINE", 390),
    ("Flap actuator", "AOG", 9800),
    ("Cockpit display unit", "AOG", 21000),
    ("Battery, main ship", "ROUTINE", 4100),
    ("Smoke detector, cargo", "ROUTINE", 610),
    ("Door seal, forward cargo", "ROUTINE", 340),
    ("Engine fan blade", "AOG", 13500),
]

PROJECT_TEMPLATES = [
    ("A-CHECK", 3), ("C-CHECK", 18), ("D-CHECK", 35), ("ENGINE-SWAP", 10),
]
TAILS = ["N804AX", "N211SK", "N337QW", "N902LT", "N558BC", "N140RM",
         "N671VP", "N303GH", "N789TD", "N226FY", "N455JK", "N912WE",
         "N600PL", "N381ZR", "N069MC"]


def build_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text())


def generate(conn: sqlite3.Connection, seed: int = SEED) -> None:
    rng = random.Random(seed)
    build_schema(conn)
    cur = conn.cursor()

    for i, (name, country) in enumerate(SUPPLIERS, start=1):
        cur.execute("INSERT INTO suppliers VALUES (?,?,?)", (i, name, country))

    for i, (desc, crit, cost) in enumerate(PART_CATALOG, start=1):
        jitter = rng.uniform(0.95, 1.05)
        cur.execute(
            "INSERT INTO parts VALUES (?,?,?,?,?)",
            (i, f"P-{1000+i}", desc, crit, round(cost * jitter, 2)),
        )
    n_parts = len(PART_CATALOG)

    projects = []
    for i, tail in enumerate(TAILS, start=1):
        check_type, duration_days = rng.choice(PROJECT_TEMPLATES)
        start_day = rng.randint(0, 300)
        code = f"{check_type}-{tail}-{2300 + i}"
        budget = rng.uniform(80_000, 650_000)
        cur.execute(
            "INSERT INTO projects VALUES (?,?,?,?,?,?,?)",
            (i, code, tail, f"{check_type} on {tail}",
             f"2025-{1 + start_day // 30:02d}-{1 + start_day % 28:02d}",
             f"2025-{1 + (start_day + duration_days) // 30:02d}-{1 + (start_day + duration_days) % 28:02d}",
             round(budget, 2)),
        )
        projects.append((i, start_day, duration_days))

    po_id = 1
    po_line_id = 1
    dn_id = 1
    dn_line_id = 1
    issue_id = 1

    for project_id, start_day, duration_days in projects:
        n_pos = rng.randint(3, 6)
        for _ in range(n_pos):
            supplier_id = rng.randint(1, len(SUPPLIERS))
            order_offset = rng.randint(0, max(1, duration_days // 2))
            order_day = start_day + order_offset
            cur.execute(
                "INSERT INTO purchase_orders VALUES (?,?,?,?,?)",
                (po_id, f"PO-{10000 + po_id}", supplier_id, project_id,
                 f"2025-{1 + order_day // 30:02d}-{1 + order_day % 28:02d}"),
            )

            n_lines = rng.randint(2, 6)
            for _ in range(n_lines):
                part_id = rng.randint(1, n_parts)
                part_cost = PART_CATALOG[part_id - 1][2]
                qty_ordered = rng.randint(1, 4) if part_cost > 5000 else rng.randint(2, 20)
                unit_price = round(part_cost * rng.uniform(0.9, 1.15), 2)
                needed_offset = order_offset + rng.randint(5, 30)
                needed_day = start_day + needed_offset
                cur.execute(
                    "INSERT INTO po_lines VALUES (?,?,?,?,?,?)",
                    (po_line_id, po_id, part_id, qty_ordered, unit_price,
                     f"2025-{1 + needed_day // 30:02d}-{1 + needed_day % 28:02d}"),
                )

                # Delivery pattern: how much of qty_ordered actually arrives
                # as accepted stock, and whether it's late.
                roll = rng.random()
                if roll < 0.65:
                    accepted_frac = 1.0
                elif roll < 0.85:
                    accepted_frac = rng.uniform(0.3, 0.85)  # backorder/short-ship
                else:
                    accepted_frac = 0.0  # nothing has arrived yet

                if accepted_frac > 0:
                    delivered = max(1, round(qty_ordered * accepted_frac))
                    rejected = 1 if rng.random() < 0.05 and delivered > 1 else 0
                    accepted = delivered - rejected
                    lateness = rng.randint(-10, 15)
                    delivery_day = needed_day + lateness
                    status = "RECEIVED" if accepted == qty_ordered else "PARTIAL"
                    cur.execute(
                        "INSERT INTO delivery_notes VALUES (?,?,?,?,?)",
                        (dn_id, f"DN-{50000 + dn_id}", po_id,
                         f"2025-{1 + max(delivery_day,0) // 30:02d}-{1 + max(delivery_day,0) % 28:02d}",
                         status),
                    )
                    cur.execute(
                        "INSERT INTO dn_lines VALUES (?,?,?,?,?,?)",
                        (dn_line_id, dn_id, po_line_id, delivered, accepted, rejected),
                    )
                    dn_id += 1
                    dn_line_id += 1

                    # Consumption: project draws down some fraction of what
                    # it actually received, against its own work orders only.
                    if accepted > 0:
                        consume_frac = rng.uniform(0.0, 1.0)
                        qty_issued = round(accepted * consume_frac)
                        if qty_issued > 0:
                            issue_day = delivery_day + rng.randint(1, 20)
                            cur.execute(
                                "INSERT INTO project_stock_issues VALUES (?,?,?,?,?,?)",
                                (issue_id, project_id, part_id, qty_issued,
                                 f"2025-{1 + max(issue_day,0) // 30:02d}-{1 + max(issue_day,0) % 28:02d}",
                                 f"WO-{project_id}-{issue_id}"),
                            )
                            issue_id += 1

                po_line_id += 1
            po_id += 1

    conn.commit()


def build_db(path: str = "airline_dn.db", seed: int = SEED) -> sqlite3.Connection:
    p = Path(path)
    if p.exists():
        p.unlink()
    conn = sqlite3.connect(path)
    generate(conn, seed)
    return conn


if __name__ == "__main__":
    conn = build_db()
    print("Seeded airline_dn.db")
    conn.close()
