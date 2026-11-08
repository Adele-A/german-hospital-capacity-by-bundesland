"""Repository paths. Everything is relative to the repo root via pathlib — no absolute
or OS-specific paths anywhere else in the code."""

from __future__ import annotations

from pathlib import Path

# etl/paths.py -> repo root is one level up from this file's parent.
REPO_ROOT = Path(__file__).resolve().parent.parent

CONFIG_DIR = REPO_ROOT / "config"
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
SQL_DIR = REPO_ROOT / "sql"
DASHBOARD_DIR = REPO_ROOT / "dashboard"
DASHBOARD_DATA_DIR = DASHBOARD_DIR / "data"
DASHBOARD_GEO_DIR = DASHBOARD_DIR / "geo"
REPORTS_DIR = REPO_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
DOCS_DIR = REPO_ROOT / "docs"

DUCKDB_PATH = WAREHOUSE_DIR / "hospitals.duckdb"
MANIFEST_PATH = RAW_DIR / "MANIFEST.json"
BUNDESLAENDER_CSV = CONFIG_DIR / "bundeslaender.csv"
SOURCES_YAML = CONFIG_DIR / "sources.yaml"


def ensure_dirs() -> None:
    """Create the output directories the pipeline writes to."""
    for d in (RAW_DIR, WAREHOUSE_DIR, DASHBOARD_DATA_DIR, DASHBOARD_GEO_DIR, FIGURES_DIR):
        d.mkdir(parents=True, exist_ok=True)
