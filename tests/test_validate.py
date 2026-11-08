"""Stage 4 — validation checks (network-free, synthetic in-memory mart)."""

import duckdb
import pandas as pd

from etl import validate, warehouse


def _fact(germany_mult: int = 16) -> pd.DataFrame:
    """16 Länder (value v) + a Germany total = germany_mult*v per additive indicator."""
    base = {"hospitals": 100.0, "beds": 1000.0, "cases": 10000.0, "bed_days": 100000.0}
    rows = []
    for ind, v in base.items():
        for i in range(1, 17):
            rows.append(
                {
                    "ags_code": f"{i:02d}",
                    "year": 2024,
                    "indicator_id": ind,
                    "value": v,
                    "unit": "x",
                    "source_id": "t",
                }
            )
        rows.append(
            {
                "ags_code": "DG",
                "year": 2024,
                "indicator_id": ind,
                "value": v * germany_mult,
                "unit": "x",
                "source_id": "t",
            }
        )
    return pd.DataFrame(rows)


def _con(fact: pd.DataFrame) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    warehouse.write_table(con, "fact_indicators", fact)
    return con


def test_parse_checks_names():
    names = {
        n
        for n, _ in validate._parse_checks(
            (validate.SQL_DIR / "checks.sql").read_text(encoding="utf-8")
        )
    }
    assert names == {"duplicates", "sixteen_laender", "no_negatives", "additivity"}


def test_sql_checks_pass_on_valid_mart():
    con = _con(_fact())
    result = validate.Result()
    validate.run_sql_checks(con, result)
    con.close()
    assert all(c["passed"] for c in result.checks), [c for c in result.checks if not c["passed"]]


def test_additivity_fails_when_total_wrong():
    con = _con(_fact(germany_mult=20))  # Germany total no longer equals the sum of Länder
    result = validate.Result()
    validate.run_sql_checks(con, result)
    con.close()
    by = {c["name"]: c["passed"] for c in result.checks}
    assert by["additivity"] is False
    assert by["sixteen_laender"] is True


def test_negative_value_flagged():
    fact = _fact()
    fact.loc[0, "value"] = -5.0
    con = _con(fact)
    result = validate.Result()
    validate.run_sql_checks(con, result)
    con.close()
    assert {c["name"]: c["passed"] for c in result.checks}["no_negatives"] is False
