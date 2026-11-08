"""Stage 2 — Extract.

Download the Destatis "Grunddaten der Krankenhäuser" reports (tokenless, idempotent) and parse
the ``csv-23111-01`` time-series sheet into a tidy long frame:
``report_key, report_year, role, ags_code, gebiet, indicator_id, wertmerkmal, masseinheit,
year, raw_value, value, flag, unit``.

Provenance (URL, sha256, timestamp, license) is written to ``data/raw/MANIFEST.json``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import openpyxl
import pandas as pd
import requests

from etl import bundeslaender, config
from etl.config import Report
from etl.paths import MANIFEST_PATH, RAW_DIR, ensure_dirs
from etl.special_values import parse_value

USER_AGENT = "german-hospital-capacity-etl/0.1 (portfolio project; contact via GitHub Adele-A)"
_TIMEOUT = 120


def _sha256(path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_reports(*, force: bool = False) -> list[dict]:
    """Download every configured report into data/raw (idempotent) and (re)write MANIFEST.json."""
    ensure_dirs()
    lic = config.license_info()
    manifest: list[dict] = []
    for rep in config.reports():
        dest = RAW_DIR / rep.filename
        if dest.exists() and not force:
            action = "reused"
        else:
            resp = requests.get(rep.url, headers={"User-Agent": USER_AGENT}, timeout=_TIMEOUT)
            resp.raise_for_status()
            if not resp.content[:4] == b"PK\x03\x04":
                raise ValueError(f"{rep.url} did not return an XLSX (bad magic bytes).")
            dest.write_bytes(resp.content)
            action = "downloaded"
        manifest.append(
            {
                "filename": rep.filename,
                "url": rep.url,
                "statistic_code": config.load_config()["statistic"]["code"],
                "report_year": rep.report_year,
                "role": rep.role,
                "series_sheet": rep.series_sheet,
                "sha256": _sha256(dest),
                "size_bytes": dest.stat().st_size,
                "downloaded_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                "action": action,
                "license": lic,
            }
        )
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def _read_sheet_rows(path, sheet: str) -> tuple[list[str], list[list]]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[sheet]
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()
    header = [bundeslaender.nfc(str(c)).strip() if c is not None else "" for c in rows[0]]
    return header, rows[1:]


def rows_to_records(header: list[str], body: list[list], rep: Report) -> list[dict]:
    """Pure parser (unit-testable): tidy source rows -> indicator records.

    Keeps only rows whose (Wertmerkmal, Masseinheit) is a configured indicator and whose Gebiet
    resolves to an AGS code. Special symbols become NaN with a flag; scaling applies only to
    real numbers.
    """
    ind_by_key = {(si.wertmerkmal, si.masseinheit): si for si in config.source_indicators()}
    records: list[dict] = []
    for raw_row in body:
        cells = [("" if c is None else bundeslaender.nfc(str(c)).strip()) for c in raw_row]
        if not any(cells):
            continue
        row = dict(zip(header, cells, strict=False))
        wm, me = row.get("Wertmerkmal", ""), row.get("Masseinheit", "")
        gebiet = row.get("Gebiet", "")
        si = ind_by_key.get((wm, me))
        if si is None:
            continue
        try:
            ags = bundeslaender.normalize_name(gebiet)
        except KeyError:
            continue  # footnote / non-region row
        try:
            year = int(float(row.get("Jahr", "")))
        except TypeError, ValueError:
            continue
        parsed = parse_value(row.get("Wert"))
        value = parsed.value if parsed.flag != "ok" else parsed.value * si.scale
        records.append(
            {
                "report_key": rep.key,
                "report_year": rep.report_year,
                "role": rep.role,
                "ags_code": ags,
                "gebiet": gebiet,
                "indicator_id": si.id,
                "wertmerkmal": wm,
                "masseinheit": me,
                "year": year,
                "raw_value": row.get("Wert", ""),
                "value": value,
                "flag": parsed.flag,
                "unit": si.unit,
            }
        )
    return records


def extract_report(rep: Report) -> pd.DataFrame:
    """Parse one report's series sheet into the tidy long frame."""
    header, body = _read_sheet_rows(RAW_DIR / rep.filename, rep.series_sheet)
    return pd.DataFrame.from_records(rows_to_records(header, body, rep))


def extract_all() -> pd.DataFrame:
    """Parse all configured reports into one long frame (rows tagged by report role)."""
    frames = [extract_report(rep) for rep in config.reports()]
    return pd.concat(frames, ignore_index=True)


def build_bundesland_long() -> pd.DataFrame:
    """By-Land mart source.

    Each report carries the 16 Länder only for its own reporting year (the sole year with Land
    detail in csv-23111-01). We take those 16-Land rows from every report, and take the
    Deutschland (DG) total for the same years from the primary national series — one consistent
    vintage. (The 2022 report's own Deutschland row and Merkmal_1 labels are quirky; the 16 Land
    rows are correct, verified by sum(Länder) == DG, so we rely only on them.)
    """
    df = extract_all()
    is_land = df["ags_code"] != bundeslaender.GERMANY_TOTAL_CODE
    land = df[is_land & (df["year"] == df["report_year"])].copy()

    years = sorted(land["year"].unique())
    germany = build_germany_series()
    germany = germany[germany["year"].isin(years)].copy()

    out = pd.concat([land, germany], ignore_index=True)
    return out.sort_values(["year", "ags_code", "indicator_id"]).reset_index(drop=True)


def build_germany_series() -> pd.DataFrame:
    """Deutschland national time series from the primary report (context: pandemic, pre-COVID)."""
    rep = config.primary_report()
    df = extract_report(rep)
    year_min = int(config.load_config()["germany_series"]["year_min"])
    out = df[(df["ags_code"] == bundeslaender.GERMANY_TOTAL_CODE) & (df["year"] >= year_min)].copy()
    return out.sort_values(["year", "indicator_id"]).reset_index(drop=True)
