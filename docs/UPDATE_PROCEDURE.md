# Update procedure — adding a new reporting year

The by-Land data for a year comes from that year's *Statistischer Bericht – Grunddaten der
Krankenhäuser* (sheet `csv-23111-01`). Adding a year is a config change plus a pipeline run.

## 1. Find the new report URL (no guessing)
On the Destatis page *Grunddaten der Krankenhäuser → Publikationen* grab the new XLSX link. The
file id encodes the year: `…2120611`**`YY`**`7005` (e.g. `…247005` = 2024). **From reporting year
2025 Destatis splits the report** into a *Deutschland* file and a separate *Bundesländer* file —
use the **Bundesländer** file, whose sheet still carries the 16 states for that year. If a year's
file cannot be located, stop — do not construct a URL.

## 2. Edit `config/sources.yaml`
- Add the new report under `reports:` with `role: primary`, its `report_year`, `series_sheet`
  (`csv-23111-01`), a `filename`, and the verified `url`. Demote the previous primary to
  `role: crosscheck`.
- Add the year to `years:` (and to `anchor_years:` if it is a headline year).
- Point `germany_series.from_report` at the new (latest) report.

## 3. Run and verify
```bash
python run_etl.py --years 2022 2023 2024 2025     # downloads the new file, rebuilds everything
```
- `data/raw/MANIFEST.json` gets the new file (URL, sha256, timestamp).
- `reports/validation_report.md` must stay **all-green** — especially additivity (Σ Länder =
  Germany total) and ALOS/occupancy vs published. If a check fails, inspect the new sheet's
  `(Wertmerkmal, Masseinheit)` labels; Destatis occasionally renames them (update
  `source_indicators` in `config/sources.yaml`).
- Static figures, the TopoJSON and `reports/dashboard_preview.html` regenerate automatically
  (needs the optional `[geo]` extra: `pip install -e ".[geo]"`).

## 4. Refresh the write-ups
Update the headline numbers in `README.md` and `reports/analytical_memo.md` to match the new mart.
Re-run the final check: delete `data/`, re-run `python run_etl.py`, confirm numbers reproduce.

## 5. Power BI
Re-import the refreshed `dashboard/data/*.csv` (same schema, so relationships and DAX are
unchanged) and, if boundaries changed, `dashboard/geo/bundeslaender.topojson`.

## Optional — switch to the GENESIS API (adds 2019–2021 by Land)
With a free `GENESIS_TOKEN` (`.env`), statistic 23111 can be pulled by Land for earlier years via
the API as the preferred source, keeping the XLSX path as the documented fallback. This is additive
— the star schema does not change.
