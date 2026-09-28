"""Build a deterministic SQLite copy of the e-commerce schema, large enough to time.

The Day 3 schema is MySQL and its seed is a few dozen rows -- fine for showing
joins, useless for showing a planner. This generates the same shape at a size
where the difference between a scan and a seek is measurable, from a fixed
seed, so every number in the README reproduces exactly.
"""

from __future__ import annotations

import random
import sqlite3
import sys
from datetime import date, timedelta

CUSTOMERS = 20_000
ORDERS = 120_000
ITEMS_PER_ORDER = (1, 4)
PRODUCTS = 600
START = date(2023, 1, 1)
DAYS = 900

# 'paid' dominates, which is the entire point of the low-selectivity finding
STATUS = (["paid"] * 90) + (["refunded"] * 7) + (["cancelled"] * 3)

COUNTRIES = ["US", "CA", "GB", "DE", "FR", "ET", "NG", "IN", "BR", "JP"]
CATEGORIES = ["Apparel", "Home", "Electronics", "Outdoor", "Grocery", "Toys"]

SCHEMA = """
PRAGMA journal_mode=DELETE;
CREATE TABLE customers (
  id         INTEGER PRIMARY KEY,
  full_name  TEXT NOT NULL,
  email      TEXT NOT NULL UNIQUE,
  country    TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE products (
  id       INTEGER PRIMARY KEY,
  name     TEXT NOT NULL,
  category TEXT NOT NULL,
  price    REAL NOT NULL CHECK (price >= 0)
);
CREATE TABLE orders (
  id          INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customers(id),
  ordered_at  TEXT NOT NULL,
  status      TEXT NOT NULL
);
CREATE TABLE order_items (
  order_id   INTEGER NOT NULL REFERENCES orders(id),
  product_id INTEGER NOT NULL REFERENCES products(id),
  quantity   INTEGER NOT NULL CHECK (quantity > 0),
  unit_price REAL NOT NULL,
  PRIMARY KEY (order_id, product_id)
) WITHOUT ROWID;
"""


def build(path: str = "shop.db", seed: int = 20260928) -> None:
    rng = random.Random(seed)
    con = sqlite3.connect(path)
    con.executescript("DROP TABLE IF EXISTS order_items; DROP TABLE IF EXISTS orders;"
                      "DROP TABLE IF EXISTS products; DROP TABLE IF EXISTS customers;")
    con.executescript(SCHEMA)

    con.executemany(
        "INSERT INTO customers VALUES (?,?,?,?,?)",
        [
            (
                i,
                f"Customer {i:05d}",
                f"c{i:05d}@example.com",
                rng.choice(COUNTRIES),
                (START + timedelta(days=rng.randrange(DAYS))).isoformat(),
            )
            for i in range(1, CUSTOMERS + 1)
        ],
    )
    con.executemany(
        "INSERT INTO products VALUES (?,?,?,?)",
        [
            (i, f"Product {i:04d}", rng.choice(CATEGORIES), round(rng.uniform(4, 400), 2))
            for i in range(1, PRODUCTS + 1)
        ],
    )

    orders, items = [], []
    for oid in range(1, ORDERS + 1):
        orders.append(
            (
                oid,
                rng.randrange(1, CUSTOMERS + 1),
                (START + timedelta(days=rng.randrange(DAYS))).isoformat(),
                rng.choice(STATUS),
            )
        )
        for pid in rng.sample(range(1, PRODUCTS + 1), rng.randint(*ITEMS_PER_ORDER)):
            items.append((oid, pid, rng.randint(1, 3), round(rng.uniform(4, 400), 2)))
    con.executemany("INSERT INTO orders VALUES (?,?,?,?)", orders)
    con.executemany("INSERT INTO order_items VALUES (?,?,?,?)", items)
    con.commit()

    n = con.execute("SELECT COUNT(*) FROM order_items").fetchone()[0]
    share = con.execute(
        "SELECT 100.0 * SUM(status='paid') / COUNT(*) FROM orders"
    ).fetchone()[0]
    print(f"{CUSTOMERS} customers, {ORDERS} orders, {n} line items, "
          f"{share:.1f}% of orders are 'paid'")
    con.close()


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "shop.db")
