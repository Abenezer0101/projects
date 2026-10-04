"""Analytics over the project-segregated DN procurement model.

Headline question: because received stock is earmarked to the project that
ordered it, can one project be short a part while another project is sitting
on unused units of the *identical* part number? If the schema's segregation
rule is doing anything at all, the answer should be yes — this script
measures how often and by how much.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "airline_dn.db"

# Per (project, part): what the project ordered vs what it actually received
# as accepted stock, and what it has issued out to its own work orders.
PROJECT_PART_POSITION = """
WITH need AS (
    SELECT po.project_id, pl.part_id, SUM(pl.qty_ordered) AS qty_needed
    FROM po_lines pl JOIN purchase_orders po ON po.po_id = pl.po_id
    GROUP BY po.project_id, pl.part_id
),
received AS (
    SELECT po.project_id, pl.part_id, SUM(dl.qty_accepted) AS qty_received
    FROM dn_lines dl
    JOIN po_lines pl ON pl.po_line_id = dl.po_line_id
    JOIN purchase_orders po ON po.po_id = pl.po_id
    GROUP BY po.project_id, pl.part_id
),
issued AS (
    SELECT project_id, part_id, SUM(qty_issued) AS qty_issued
    FROM project_stock_issues
    GROUP BY project_id, part_id
)
SELECT
    n.project_id, n.part_id,
    n.qty_needed,
    COALESCE(r.qty_received, 0) AS qty_received,
    COALESCE(i.qty_issued, 0) AS qty_issued,
    MAX(n.qty_needed - COALESCE(r.qty_received, 0), 0) AS shortfall,
    MAX(COALESCE(r.qty_received, 0) - COALESCE(i.qty_issued, 0), 0) AS idle_surplus
FROM need n
LEFT JOIN received r ON r.project_id = n.project_id AND r.part_id = n.part_id
LEFT JOIN issued i ON i.project_id = n.project_id AND i.part_id = n.part_id
"""


def positions(conn):
    return conn.execute(PROJECT_PART_POSITION).fetchall()


def stranded_coverage(conn):
    """For every shortfall, how much of it could another project's idle
    surplus of the same part number have covered, were stock pooled instead
    of project-segregated? Greedy match per part, largest surplus first."""
    rows = positions(conn)
    by_part = {}
    for project_id, part_id, needed, received, issued, shortfall, idle in rows:
        by_part.setdefault(part_id, []).append(
            {"project_id": project_id, "needed": needed, "received": received,
             "issued": issued, "shortfall": shortfall, "idle": idle}
        )

    cases = []
    for part_id, rows_for_part in by_part.items():
        shortages = [r for r in rows_for_part if r["shortfall"] > 0]
        surpluses = sorted(
            (r for r in rows_for_part if r["idle"] > 0),
            key=lambda r: -r["idle"],
        )
        for s in shortages:
            remaining = s["shortfall"]
            for surplus_owner in surpluses:
                if surplus_owner["project_id"] == s["project_id"] or remaining <= 0:
                    continue
                coverable = min(remaining, surplus_owner["idle"])
                if coverable > 0:
                    cases.append({
                        "part_id": part_id,
                        "short_project": s["project_id"],
                        "shortfall": s["shortfall"],
                        "surplus_project": surplus_owner["project_id"],
                        "surplus_available": surplus_owner["idle"],
                        "coverable": coverable,
                    })
                    remaining -= coverable
    return cases


def part_label(conn, part_id):
    return conn.execute(
        "SELECT part_number, description FROM parts WHERE part_id = ?", (part_id,)
    ).fetchone()


def project_label(conn, project_id):
    return conn.execute(
        "SELECT project_code FROM projects WHERE project_id = ?", (project_id,)
    ).fetchone()[0]


def on_time_delivery_by_supplier(conn):
    return conn.execute("""
        SELECT s.name,
               COUNT(*) AS deliveries,
               SUM(CASE WHEN dn.delivery_date <= pl.needed_by THEN 1 ELSE 0 END) AS on_time
        FROM delivery_notes dn
        JOIN purchase_orders po ON po.po_id = dn.po_id
        JOIN suppliers s ON s.supplier_id = po.supplier_id
        JOIN dn_lines dl ON dl.dn_id = dn.dn_id
        JOIN po_lines pl ON pl.po_line_id = dl.po_line_id
        GROUP BY s.supplier_id
        ORDER BY on_time * 1.0 / deliveries ASC
    """).fetchall()


def lead_time_by_criticality(conn):
    return conn.execute("""
        SELECT p.criticality,
               AVG(julianday(dn.delivery_date) - julianday(po.order_date)) AS avg_lead_days
        FROM delivery_notes dn
        JOIN purchase_orders po ON po.po_id = dn.po_id
        JOIN dn_lines dl ON dl.dn_id = dn.dn_id
        JOIN po_lines pl ON pl.po_line_id = dl.po_line_id
        JOIN parts p ON p.part_id = pl.part_id
        GROUP BY p.criticality
    """).fetchall()


def main():
    conn = sqlite3.connect(DB_PATH)

    cases = stranded_coverage(conn)
    total_shortfall_units = sum(r[5] for r in positions(conn) if r[5] > 0)
    total_coverable = sum(c["coverable"] for c in cases)

    print(f"Total project-level shortfall across the fleet: {total_shortfall_units} units")
    print(f"Of that, units sitting idle in another project's segregated stock "
          f"for the identical part: {total_coverable} units "
          f"({total_coverable / total_shortfall_units:.0%})\n")

    cases.sort(key=lambda c: -c["coverable"])
    print("Biggest cases (shortfall that stranded stock elsewhere could have covered):")
    for c in cases[:5]:
        pn, desc = part_label(conn, c["part_id"])
        short_code = project_label(conn, c["short_project"])
        surplus_code = project_label(conn, c["surplus_project"])
        print(f"  {pn} ({desc}): {short_code} is short {c['shortfall']} units, "
              f"while {surplus_code} holds {c['surplus_available']} unused "
              f"-> {c['coverable']} units stranded")

    print("\nSupplier on-time delivery rate (line-level, worst first):")
    for name, deliveries, on_time in on_time_delivery_by_supplier(conn):
        print(f"  {name}: {on_time}/{deliveries} ({on_time / deliveries:.0%})")

    print("\nAvg lead time (order -> delivery) by part criticality:")
    for crit, avg_days in lead_time_by_criticality(conn):
        print(f"  {crit}: {avg_days:.1f} days")

    conn.close()


if __name__ == "__main__":
    main()
