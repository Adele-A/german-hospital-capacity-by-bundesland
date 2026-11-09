"""Stage 3 — mart derivation and dimensions (network-free, in-memory DuckDB)."""

import duckdb
import pandas as pd
import pytest

from etl import indicators, transform, warehouse
from etl.paths import SQL_DIR


def _stg(year: int) -> pd.DataFrame:
    """One synthetic region/year with internally consistent published per-100k."""
    rows = {
        "hospitals": 30.0,
        "beds": 1000.0,
        "cases": 500000.0,
        "bed_days": 300000.0,
        "beds_per_100k_published": 50.0,  # implies population 2,000,000
        "cases_per_100k_published": 25000.0,  # also implies 2,000,000
        "alos_published": 0.6,
        "occupancy_published": 81.97 if year == 2024 else 82.19,
    }
    return pd.DataFrame(
        [
            {
                "ags_code": "08",
                "year": year,
                "indicator_id": k,
                "value": v,
                "unit": "x",
                "flag": "ok",
                "source_id": "test",
            }
            for k, v in rows.items()
        ]
    )


def _build(year: int) -> dict:
    con = duckdb.connect(":memory:")
    warehouse.write_table(con, "stg_hospital_long", _stg(year))
    warehouse.run_script(con, (SQL_DIR / "mart.sql").read_text(encoding="utf-8"))
    row = con.cursor().execute("SELECT * FROM mart_wide").df().iloc[0].to_dict()
    con.close()
    return row


def test_population_recovered_and_consistent():
    r = _build(2024)
    assert r["population_avg"] == pytest.approx(2_000_000)
    assert r["population_avg_from_cases"] == pytest.approx(2_000_000)


def test_per_100k_recomputed_equals_published():
    r = _build(2024)
    assert r["beds_per_100k"] == pytest.approx(r["beds_per_100k_published"])
    assert r["cases_per_100k"] == pytest.approx(r["cases_per_100k_published"])


def test_alos_is_bed_days_over_cases():
    r = _build(2024)
    assert r["alos"] == pytest.approx(300000 / 500000)


def test_occupancy_uses_leap_year_days():
    leap = _build(2024)  # 366 days
    non_leap = _build(2023)  # 365 days
    assert leap["days_in_year"] == 366
    assert non_leap["days_in_year"] == 365
    assert leap["occupancy"] == pytest.approx(300000 / (1000 * 366) * 100)
    assert non_leap["occupancy"] == pytest.approx(300000 / (1000 * 365) * 100)


def test_fact_indicators_has_source_and_derived():
    con = duckdb.connect(":memory:")
    warehouse.write_table(con, "stg_hospital_long", _stg(2024))
    warehouse.run_script(con, (SQL_DIR / "mart.sql").read_text(encoding="utf-8"))
    got = {
        r[0]
        for r in con.cursor()
        .execute("SELECT DISTINCT indicator_id FROM fact_indicators")
        .fetchall()
    }
    con.close()
    assert {"hospitals", "beds", "cases", "bed_days"} <= got  # source
    assert {
        "population_avg",
        "beds_per_100k",
        "cases_per_100k",
        "alos",
        "occupancy",
    } <= got  # derived


def test_germany_series_wide_from_long(monkeypatch):
    """build_germany_series pivots the DG long series to a wide national table."""
    long = pd.DataFrame(
        [
            {"year": y, "indicator_id": ind, "value": v}
            for y in (2019, 2024)
            for ind, v in {
                "hospitals": 1900.0,
                "beds": 480000.0,
                "cases": 1.9e7,
                "bed_days": 1.2e8,
                "beds_per_100k_published": 580.0,
                "cases_per_100k_published": 23000.0,
                "alos_published": 6.3,
                "occupancy_published": 70.0,
            }.items()
        ]
    )
    monkeypatch.setattr(transform.extract, "build_germany_series", lambda: long)
    con = duckdb.connect(":memory:")
    n = transform.build_germany_series(con)
    df = con.cursor().execute("SELECT * FROM fact_germany_series ORDER BY year").df()
    con.close()
    assert n == 2
    assert list(df["year"]) == [2019, 2024]
    # population_avg recovered from published per-100k: 480000 / 580 * 1e5
    assert df.loc[0, "population_avg"] == pytest.approx(480000 / 580 * 100000)
    assert df.loc[0, "beds_per_100k"] == 580.0 and df.loc[0, "alos"] == 6.3


def test_dims_built_without_network():
    con = duckdb.connect(":memory:")
    transform.build_dims(con)
    di = con.cursor().execute("SELECT indicator_id, name_de, name_en FROM dim_indicator").df()
    assert set(di["indicator_id"]) == set(indicators.indicator_ids())
    assert di["name_de"].notna().all() and di["name_en"].notna().all()
    dy = (
        con.cursor()
        .execute("SELECT year, population_census_basis FROM dim_year ORDER BY year")
        .df()
    )
    basis = dict(zip(dy["year"], dy["population_census_basis"], strict=True))
    assert basis[2022] == "Zensus 2022"  # series break after Zensus 2022
    con.close()
