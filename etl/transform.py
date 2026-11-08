"""Stage 3 — Transform. Build the staging table, dimensions, and the mart (via sql/mart.sql)."""

from __future__ import annotations

import duckdb
import pandas as pd

from etl import bundeslaender, config, extract, indicators, warehouse
from etl.paths import SQL_DIR


def _source_id(report_key: str) -> str:
    return f"destatis_23111_sb_{report_key}"


def build_staging(con: duckdb.DuckDBPyConnection) -> int:
    """stg_hospital_long: the by-Land source rows (+ Germany total) with provenance."""
    df = extract.build_bundesland_long()
    stg = pd.DataFrame(
        {
            "ags_code": df["ags_code"],
            "year": df["year"].astype(int),
            "indicator_id": df["indicator_id"],
            "value": df["value"],
            "unit": df["unit"],
            "flag": df["flag"],
            "source_id": df["report_key"].map(_source_id),
        }
    )
    return warehouse.write_table(con, "stg_hospital_long", stg)


def build_dims(con: duckdb.DuckDBPyConnection) -> None:
    """dim_bundesland, dim_indicator, dim_year."""
    ref = pd.DataFrame(
        [
            {
                "ags_code": b.ags_code,
                "iso_3166_2": b.iso_3166_2,
                "name_de": b.name_de,
                "name_en": b.name_en,
                "is_total": b.is_total,
            }
            for b in bundeslaender.load_reference()
        ]
    )
    dim_ind = pd.DataFrame(indicators.INDICATORS)
    dim_ind["source_table"] = indicators.SOURCE_TABLE
    dim_ind["source_url"] = indicators.SOURCE_URL
    dim_ind["license"] = indicators.LICENSE

    years = sorted(config.years())
    dim_year = pd.DataFrame(
        {
            "year": years,
            "is_anchor": [y in config.anchor_years() for y in years],
            "covid_affected": [y in (2020, 2021, 2022) for y in years],
            "population_census_basis": [
                "Zensus 2022" if y >= 2022 else "Zensus 2011" for y in years
            ],
        }
    )
    for name, frame in (
        ("dim_bundesland", ref),
        ("dim_indicator", dim_ind),
        ("dim_year", dim_year),
    ):
        warehouse.write_table(con, name, frame)


def build_mart(con: duckdb.DuckDBPyConnection) -> None:
    """Run sql/mart.sql to produce mart_wide, fact_indicators, fact_indicators_wide."""
    warehouse.run_script(con, (SQL_DIR / "mart.sql").read_text(encoding="utf-8"))


def run_transform(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    build_staging(con)
    build_dims(con)
    build_mart(con)
    tables = ["stg_hospital_long", "mart_wide", "fact_indicators", "fact_indicators_wide"]
    return {t: warehouse.count(con, t) for t in tables}
