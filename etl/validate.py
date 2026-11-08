"""Stage 4 — Validate. Runs SQL checks + a pandera schema, cross-checks recomputed vs published
values, flags large year-on-year moves, traces a few mart cells back to source, and writes
reports/validation_report.md. Hard failures raise ValidationError so the pipeline fails loudly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import openpyxl
import pandas as pd
import pandera.pandas as pa

from etl import bundeslaender, config
from etl.paths import RAW_DIR, REPORTS_DIR, SQL_DIR

YOY_FLAG_PCT = 15.0
ALOS_OCC_TOL = 0.05  # published values are rounded to 2 dp


class ValidationError(AssertionError):
    pass


@dataclass
class Result:
    checks: list[dict] = field(default_factory=list)
    hard_failures: list[str] = field(default_factory=list)

    def add(self, name: str, passed: bool, detail: str, *, hard: bool = True) -> None:
        self.checks.append({"name": name, "passed": passed, "detail": detail})
        if hard and not passed:
            self.hard_failures.append(f"{name}: {detail}")


# ---- SQL checks (sql/checks.sql) ----------------------------------------------------------


def _parse_checks(sql: str) -> list[tuple[str, str]]:
    """Parse named checks. Line-based so a ';' inside a comment never splits a statement."""
    out: list[tuple[str, str]] = []
    name: str | None = None
    buf: list[str] = []
    for line in sql.splitlines():
        m = re.match(r"\s*--\s*name:\s*(\w+)", line)
        if m:
            name = m.group(1)
        code = line.split("--", 1)[0]  # strip comment (and any ';' inside it)
        buf.append(code)
        if ";" in code:
            stmt = "\n".join(buf).split(";", 1)[0].strip()
            if name and stmt:
                out.append((name, stmt))
            name, buf = None, []
    return out


def run_sql_checks(con, result: Result) -> None:
    for name, query in _parse_checks((SQL_DIR / "checks.sql").read_text(encoding="utf-8")):
        rows = con.cursor().execute(query).fetchall()
        result.add(
            name, not rows, "ok" if not rows else f"{len(rows)} offending row(s): {rows[:5]}"
        )


# ---- pandera schema -----------------------------------------------------------------------


def schema_check(con, result: Result) -> None:
    df = con.cursor().execute("SELECT * FROM fact_indicators_wide").df()
    schema = pa.DataFrameSchema(
        {
            "ags_code": pa.Column(str),
            "year": pa.Column(int, pa.Check.isin(config.years())),
            "hospitals": pa.Column(float, pa.Check.gt(0)),
            "beds": pa.Column(float, pa.Check.gt(0)),
            "cases": pa.Column(float, pa.Check.gt(0)),
            "bed_days": pa.Column(float, pa.Check.gt(0)),
            "population_avg": pa.Column(float, pa.Check.gt(0)),
            "beds_per_100k": pa.Column(float, pa.Check.in_range(100, 1500)),
            "cases_per_100k": pa.Column(float, pa.Check.gt(0)),
            "alos": pa.Column(float, pa.Check.in_range(3, 15)),
            "occupancy": pa.Column(float, pa.Check.in_range(0, 100)),
        }
    )
    try:
        schema.validate(df, lazy=True)
        result.add("pandera_schema", True, f"{len(df)} rows conform")
    except pa.errors.SchemaErrors as exc:
        result.add("pandera_schema", False, f"{len(exc.failure_cases)} failure case(s)")


# ---- recomputed vs published --------------------------------------------------------------


def recompute_checks(con, result: Result) -> pd.DataFrame:
    df = con.cursor().execute("SELECT * FROM mart_wide").df()
    df["pop_xcheck_pct"] = (
        (df["population_avg"] - df["population_avg_from_cases"]).abs() / df["population_avg"] * 100
    )
    df["beds_per_100k_absdiff"] = (df["beds_per_100k"] - df["beds_per_100k_published"]).abs()
    df["cases_per_100k_absdiff"] = (df["cases_per_100k"] - df["cases_per_100k_published"]).abs()
    df["alos_absdiff"] = (df["alos"] - df["alos_published"]).abs()
    df["occupancy_absdiff"] = (df["occupancy"] - df["occupancy_published"]).abs()
    per100k_max = max(df["beds_per_100k_absdiff"].max(), df["cases_per_100k_absdiff"].max())

    result.add(
        "population_cross_check",
        df["pop_xcheck_pct"].max() < 0.01,
        f"beds-vs-cases implied population max diff {df['pop_xcheck_pct'].max():.4f}%",
    )
    result.add(
        "per_100k_reproduces_published",
        per100k_max < 1e-6,
        f"max abs diff {per100k_max:.2e}",
    )
    result.add(
        "alos_matches_published",
        df["alos_absdiff"].max() <= ALOS_OCC_TOL,
        f"max abs diff {df['alos_absdiff'].max():.4f} days",
    )
    result.add(
        "occupancy_matches_published",
        df["occupancy_absdiff"].max() <= ALOS_OCC_TOL,
        f"max abs diff {df['occupancy_absdiff'].max():.4f} %-points",
    )
    return df


# ---- year-on-year flags (informational) ---------------------------------------------------


def yoy_flags(con) -> pd.DataFrame:
    df = (
        con.cursor()
        .execute(
            "SELECT ags_code, year, indicator_id, value FROM fact_indicators WHERE ags_code <> 'DG'"
        )
        .df()
    )
    df = df.sort_values(["ags_code", "indicator_id", "year"])
    df["pct"] = df.groupby(["ags_code", "indicator_id"])["value"].pct_change() * 100
    flags = df[df["pct"].abs() > YOY_FLAG_PCT].dropna(subset=["pct"]).copy()
    return flags


# ---- manual spot-checks (mart cell -> source cell) ---------------------------------------

SPOT_CHECKS = [
    ("2024", "Berlin", "Patientenbewegung Fallzahl", "Anzahl", "cases", "11", 2024, 1),
    (
        "2023",
        "Bayern",
        "Krankenhäuser aufgestellte Betten insgesamt",
        "Anzahl",
        "beds",
        "09",
        2023,
        1,
    ),
    ("2022", "Sachsen", "Krankenhäuser insgesamt", "Anzahl", "hospitals", "14", 2022, 1),
    (
        "2024",
        "Hamburg",
        "Patientenbewegung Berechnungs-/ Belegungstage",
        "in 1000",
        "bed_days",
        "02",
        2024,
        1000,
    ),
]


def _raw_cell(report_key: str, gebiet: str, wertmerkmal: str, masseinheit: str) -> str | None:
    rep = next(r for r in config.reports() if r.key == report_key)
    wb = openpyxl.load_workbook(RAW_DIR / rep.filename, read_only=True, data_only=True)
    try:
        ws = wb[rep.series_sheet]
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()
    header = [bundeslaender.nfc(str(c)).strip() if c is not None else "" for c in rows[0]]
    for raw in rows[1:]:
        d = dict(
            zip(
                header,
                [("" if c is None else bundeslaender.nfc(str(c)).strip()) for c in raw],
                strict=False,
            )
        )
        if (
            d.get("Gebiet", "").strip() == gebiet
            and d.get("Wertmerkmal") == wertmerkmal
            and d.get("Masseinheit") == masseinheit
        ):
            return d.get("Wert")
    return None


def spot_checks(con, result: Result) -> list[dict]:
    out: list[dict] = []
    for report_key, gebiet, wm, me, ind, ags, year, scale in SPOT_CHECKS:
        raw = _raw_cell(report_key, gebiet, wm, me)
        mart = (
            con.cursor()
            .execute(
                "SELECT value FROM fact_indicators WHERE ags_code=? AND year=? AND indicator_id=?",
                [ags, year, ind],
            )
            .fetchone()
        )
        mart_val = mart[0] if mart else None
        expected = float(raw) * scale if raw is not None else None
        ok = expected is not None and mart_val is not None and abs(expected - mart_val) < 1e-6
        out.append(
            {
                "cell": f"{gebiet} / {wm} / {me} ({report_key} report, sheet csv-23111-01)",
                "raw": raw,
                "scale": scale,
                "mart": mart_val,
                "indicator": ind,
                "ok": ok,
            }
        )
    result.add(
        "manual_spot_checks",
        all(c["ok"] for c in out),
        f"{sum(c['ok'] for c in out)}/{len(out)} cells trace to source",
    )
    return out


# ---- report ------------------------------------------------------------------------------


def _fmt(x: object) -> str:
    return f"{x:,.2f}" if isinstance(x, float) else str(x)


def write_report(
    con, result: Result, recompute: pd.DataFrame, flags: pd.DataFrame, spots: list[dict]
) -> None:
    lic = config.license_info()
    lines: list[str] = []
    w = lines.append
    w("# Validation report\n")
    w(
        "Automated data-quality checks for the hospital-capacity mart. Generated by "
        "`etl/validate.py` (run via `python run_etl.py`). Hard checks fail the pipeline; "
        "year-on-year flags are review items, not errors.\n"
    )
    w(f"- **Years (by Land):** {', '.join(map(str, config.years()))}")
    w("- **Scope:** 16 Bundesländer + Germany total (DG), 9 indicators")
    w(f"- **Source:** {lic['attribution']}, statistic 23111 — license {lic['name']}\n")

    passed = sum(c["passed"] for c in result.checks)
    w(f"## Summary — {passed}/{len(result.checks)} checks passed\n")
    w("| Check | Result | Detail |")
    w("|---|---|---|")
    for c in result.checks:
        w(f"| `{c['name']}` | {'✅ pass' if c['passed'] else '❌ FAIL'} | {c['detail']} |")
    w("")

    w("## Additivity — sum of 16 Länder vs Germany total\n")
    add = (
        con.cursor()
        .execute(
            """SELECT year, indicator_id, sum(value) FILTER (WHERE ags_code<>'DG') AS sum_laender,
                  max(value) FILTER (WHERE ags_code='DG') AS germany
           FROM fact_indicators
           WHERE indicator_id IN ('hospitals','beds','cases','bed_days')
           GROUP BY year, indicator_id ORDER BY indicator_id, year"""
        )
        .df()
    )
    add["pct_diff"] = (add["sum_laender"] - add["germany"]).abs() / add["germany"] * 100
    w("| Year | Indicator | Σ Länder | Germany | % diff |")
    w("|---|---|--:|--:|--:|")
    for _, r in add.iterrows():
        w(
            f"| {r['year']} | {r['indicator_id']} | {r['sum_laender']:,.1f} | {r['germany']:,.1f} "
            f"| {r['pct_diff']:.4f}% |"
        )
    w("")

    w("## Recomputed vs Destatis-published\n")
    w(
        "Per-100k reproduce the published rates exactly (population recovered from them). ALOS and "
        "occupancy are **independent** recomputations and match the published values to rounding.\n"
    )
    w(
        f"- population (beds-implied vs cases-implied): max diff "
        f"**{recompute['pop_xcheck_pct'].max():.4f}%**"
    )
    per100k_max = max(
        recompute["beds_per_100k_absdiff"].max(), recompute["cases_per_100k_absdiff"].max()
    )
    w(f"- beds/cases per 100k vs published: max abs diff **{per100k_max:.2e}**")
    w(
        f"- ALOS = bed_days/cases vs published: max abs diff "
        f"**{recompute['alos_absdiff'].max():.4f} days**"
    )
    w(
        f"- occupancy = bed_days/(beds×days) vs published: max abs diff "
        f"**{recompute['occupancy_absdiff'].max():.4f} %-points**\n"
    )

    w(f"## Year-on-year flags (|Δ| > {YOY_FLAG_PCT:.0f}%) — review items, not errors\n")
    if flags.empty:
        w("None: all consecutive-year moves are within ±15%.\n")
    else:
        w("| Land | Indicator | Year | % change |")
        w("|---|---|--:|--:|")
        for _, r in flags.iterrows():
            w(f"| {r['ags_code']} | {r['indicator_id']} | {int(r['year'])} | {r['pct']:+.1f}% |")
        w("")

    w("## Manual spot-checks (mart cell → source cell)\n")
    w("| Source cell | Raw | ×scale | Mart | ✓ |")
    w("|---|--:|--:|--:|:-:|")
    for c in spots:
        w(
            f"| {c['cell']} → `{c['indicator']}` | {c['raw']} | ×{c['scale']} | {_fmt(c['mart'])} "
            f"| {'✅' if c['ok'] else '❌'} |"
        )
    w("")

    w("## Notes on comparability\n")
    w(
        "- **COVID-19:** 2020–2021 saw depressed case counts; 2022 is still partly affected, with "
        "recovery through 2023–2024. By-Land years here are 2022–2024; the national series (not in "
        "this mart) extends back to the pre-pandemic baseline."
    )
    w(
        "- **Zensus 2022 series break:** population from 2022 onward uses the new census basis "
        "(earlier years use Zensus 2011), affecting per-100k comparisons across that boundary."
    )
    w(
        '- **"Fälle" ≠ unique patients**, and cases are counted at the hospital\'s location, not '
        "the patient's residence — relevant for city-states and the Berlin–Brandenburg pair.\n"
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_validation(con, *, strict: bool = True) -> Result:
    result = Result()
    run_sql_checks(con, result)
    schema_check(con, result)
    recompute = recompute_checks(con, result)
    flags = yoy_flags(con)
    spots = spot_checks(con, result)
    write_report(con, result, recompute, flags, spots)
    if strict and result.hard_failures:
        raise ValidationError("; ".join(result.hard_failures))
    return result
