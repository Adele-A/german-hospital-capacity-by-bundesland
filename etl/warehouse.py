"""DuckDB warehouse helpers (layers: raw -> staging -> mart)."""

from __future__ import annotations

import duckdb
import pandas as pd

from etl.paths import DUCKDB_PATH, ensure_dirs


def connect() -> duckdb.DuckDBPyConnection:
    ensure_dirs()
    return duckdb.connect(str(DUCKDB_PATH))


def write_table(con: duckdb.DuckDBPyConnection, name: str, df: pd.DataFrame) -> int:
    """Replace a table with the contents of a pandas DataFrame. Returns the row count."""
    con.register("_df_tmp", df)
    con.execute(f'CREATE OR REPLACE TABLE "{name}" AS SELECT * FROM _df_tmp')
    con.unregister("_df_tmp")
    return con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]


def table_names(con: duckdb.DuckDBPyConnection) -> list[str]:
    return [r[0] for r in con.execute("SHOW TABLES").fetchall()]
