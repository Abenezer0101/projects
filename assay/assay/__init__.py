"""assay -- a dependency-free data quality gate that also audits its own rules."""
from .engine import Report, read_csv, run, split, write_csv
from .mutate import Audit, audit
from .rules import ERROR, WARN
from .spec import Suite, SpecError, load_spec

__version__ = "0.1.0"
__all__ = ["run", "audit", "load_spec", "read_csv", "write_csv", "split",
           "Report", "Audit", "Suite", "SpecError", "ERROR", "WARN"]
