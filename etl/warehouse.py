"""DuckDB warehouse helpers (layers: raw -> staging -> mart)."""

from __future__ import annotations

import duckdb
import pandas as pd

from etl.paths import DUCKDB_PATH, ensure_dirs


def connect() -> duckdb.DuckDBPyConnection:
    ensure_dirs()
    return duckdb.connect(str(DUCKDB_PATH))


def write_table(con: duckdb.DuckDBPyConnection, name: str, df: pd.DataFrame) -> int:
    """Replace a table with the contents of a pandas DataFrame. Returns the row count.

    Runs on its own cursor so sequential writes never collide on open result state.
    """
    cur = con.cursor()
    try:
        cur.register("_df_tmp", df)
        cur.execute(f'CREATE OR REPLACE TABLE "{name}" AS SELECT * FROM _df_tmp')
        cur.unregister("_df_tmp")
        return cur.execute(f'SELECT count(*) FROM "{name}"').fetchall()[0][0]
    finally:
        cur.close()


def run_script(con: duckdb.DuckDBPyConnection, sql: str) -> None:
    """Execute a multi-statement SQL script, draining each result."""
    # Strip line comments first so a ';' inside a comment can't split a statement.
    code = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())
    cur = con.cursor()
    try:
        for statement in (s.strip() for s in code.split(";")):
            if not statement:
                continue
            res = cur.execute(statement)
            if res is not None:
                res.fetchall()
    finally:
        cur.close()


def count(con: duckdb.DuckDBPyConnection, name: str) -> int:
    return con.cursor().execute(f'SELECT count(*) FROM "{name}"').fetchall()[0][0]


def table_names(con: duckdb.DuckDBPyConnection) -> list[str]:
    return [r[0] for r in con.cursor().execute("SHOW TABLES").fetchall()]
