-- Airline MRO procurement, project-segregated stock.
-- Every receipt and every issue is tied to a project (a maintenance work
-- package against one tail number), never to a plant-wide pool. That's the
-- real-world constraint this schema encodes: two projects can hold the same
-- part number and never see each other's stock.

PRAGMA foreign_keys = ON;

CREATE TABLE suppliers (
    supplier_id   INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    country       TEXT NOT NULL
);

CREATE TABLE parts (
    part_id       INTEGER PRIMARY KEY,
    part_number   TEXT NOT NULL UNIQUE,
    description   TEXT NOT NULL,
    criticality   TEXT NOT NULL CHECK (criticality IN ('ROUTINE', 'AOG')),
    unit_cost     REAL NOT NULL CHECK (unit_cost > 0)
);

CREATE TABLE projects (
    project_id    INTEGER PRIMARY KEY,
    project_code  TEXT NOT NULL UNIQUE,   -- e.g. 'C-CHECK-N804AX-2301'
    aircraft_tail TEXT NOT NULL,
    description   TEXT NOT NULL,
    start_date    TEXT NOT NULL,
    end_date      TEXT NOT NULL,
    budget        REAL NOT NULL CHECK (budget > 0)
);

CREATE TABLE purchase_orders (
    po_id         INTEGER PRIMARY KEY,
    po_number     TEXT NOT NULL UNIQUE,
    supplier_id   INTEGER NOT NULL REFERENCES suppliers(supplier_id),
    project_id    INTEGER NOT NULL REFERENCES projects(project_id),
    order_date    TEXT NOT NULL
);

-- Account-assignment category 'Q' lines: each line is earmarked to the PO's
-- project. Stock received against it can legally be consumed only by that
-- project, no matter what part_id it shares with other projects.
CREATE TABLE po_lines (
    po_line_id    INTEGER PRIMARY KEY,
    po_id         INTEGER NOT NULL REFERENCES purchase_orders(po_id),
    part_id       INTEGER NOT NULL REFERENCES parts(part_id),
    qty_ordered   INTEGER NOT NULL CHECK (qty_ordered > 0),
    unit_price    REAL NOT NULL CHECK (unit_price > 0),
    needed_by     TEXT NOT NULL
);

CREATE TABLE delivery_notes (
    dn_id         INTEGER PRIMARY KEY,
    dn_number     TEXT NOT NULL UNIQUE,
    po_id         INTEGER NOT NULL REFERENCES purchase_orders(po_id),
    delivery_date TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('RECEIVED', 'PARTIAL', 'REJECTED'))
);

CREATE TABLE dn_lines (
    dn_line_id    INTEGER PRIMARY KEY,
    dn_id         INTEGER NOT NULL REFERENCES delivery_notes(dn_id),
    po_line_id    INTEGER NOT NULL REFERENCES po_lines(po_line_id),
    qty_delivered INTEGER NOT NULL CHECK (qty_delivered >= 0),
    qty_accepted  INTEGER NOT NULL CHECK (qty_accepted >= 0),
    qty_rejected  INTEGER NOT NULL CHECK (qty_rejected >= 0),
    CHECK (qty_accepted + qty_rejected = qty_delivered)
);

-- Consumption against a project's own segregated stock bucket.
CREATE TABLE project_stock_issues (
    issue_id      INTEGER PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(project_id),
    part_id       INTEGER NOT NULL REFERENCES parts(part_id),
    qty_issued    INTEGER NOT NULL CHECK (qty_issued > 0),
    issue_date    TEXT NOT NULL,
    work_order_ref TEXT NOT NULL
);

CREATE INDEX idx_po_lines_part ON po_lines(part_id);
CREATE INDEX idx_po_lines_po ON po_lines(po_id);
CREATE INDEX idx_dn_lines_po_line ON dn_lines(po_line_id);
CREATE INDEX idx_issues_project_part ON project_stock_issues(project_id, part_id);
CREATE INDEX idx_pos_project ON purchase_orders(project_id);
