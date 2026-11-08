"""Stage 5 — CSV export (network-free, no geo deps required)."""

import duckdb
import pandas as pd

from etl import export, warehouse


def _con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    warehouse.write_table(
        con,
        "fact_indicators",
        pd.DataFrame(
            [
                {
                    "ags_code": "11",
                    "year": 2024,
                    "indicator_id": "beds",
                    "value": 20119.0,
                    "unit": "count",
                    "source_id": "t",
                }
            ]
        ),
    )
    warehouse.write_table(
        con,
        "fact_indicators_wide",
        pd.DataFrame([{"ags_code": "11", "year": 2024, "beds": 20119.0, "beds_per_100k": 547.63}]),
    )
    warehouse.write_table(
        con,
        "dim_bundesland",
        pd.DataFrame(
            [{"ags_code": "11", "name_de": "Berlin", "name_en": "Berlin", "is_total": False}]
        ),
    )
    warehouse.write_table(con, "dim_indicator", pd.DataFrame([{"indicator_id": "beds"}]))
    warehouse.write_table(con, "dim_year", pd.DataFrame([{"year": 2024}]))
    return con


def test_export_writes_all_tables(tmp_path):
    con = _con()
    counts = export.export_csvs(con, out_dir=tmp_path)
    con.close()
    for name in export.EXPORT_TABLES:
        assert (tmp_path / f"{name}.csv").is_file()
    assert counts["fact_indicators"] == 1


def test_csv_is_utf8_with_point_decimal(tmp_path):
    con = _con()
    export.export_csvs(con, out_dir=tmp_path)
    con.close()
    text = (tmp_path / "fact_indicators_wide.csv").read_text(encoding="utf-8")
    assert "547.63" in text  # '.' decimal separator, readable as UTF-8
    assert "Berlin" in (tmp_path / "dim_bundesland.csv").read_text(encoding="utf-8")
