"""Stage 5 — Export. Write the star-schema CSVs for Power BI and (separately) build the geo
TopoJSON, static figures and the self-contained Plotly HTML preview."""

from __future__ import annotations

from pathlib import Path

import duckdb

from etl.paths import DASHBOARD_DATA_DIR

# Published to dashboard/data as UTF-8 CSV with a '.' decimal separator (Power BI friendly).
EXPORT_TABLES = [
    "fact_indicators",
    "fact_indicators_wide",
    "dim_bundesland",
    "dim_indicator",
    "dim_year",
]


def export_csvs(con: duckdb.DuckDBPyConnection, out_dir: Path | None = None) -> dict[str, int]:
    """Write the star-schema tables to <out_dir>/*.csv (UTF-8, '.' decimal)."""
    out_dir = out_dir or DASHBOARD_DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for name in EXPORT_TABLES:
        df = con.cursor().execute(f'SELECT * FROM "{name}" ORDER BY ALL').df()
        df.to_csv(out_dir / f"{name}.csv", index=False, encoding="utf-8")
        counts[name] = len(df)
    return counts
