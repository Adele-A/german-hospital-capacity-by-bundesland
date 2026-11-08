# German Hospital System by Bundesland — Capacity & Utilisation

Reproducible ETL + BI comparing hospital capacity and utilisation across the **16 German federal
states (Bundesländer)** using official **Destatis** statistics, with a focus on **Berlin–
Brandenburg**. Independent data-analytics portfolio project.

> 🚧 **Work in progress.** This README is filled in as the pipeline is built (see
> [`docs/PLAN.md`](docs/PLAN.md) for the full plan and verified sources). Key numbers, figures
> and the dashboard specification are added stage by stage.

## What this is

- **Sources:** Destatis *Grunddaten der Krankenhäuser* (statistic 23111) and *Fortschreibung des
  Bevölkerungsstandes* (statistic 12411). Every indicator is traceable to a named source table.
- **Stack:** Python 3.14, DuckDB (`raw → staging → mart`), Power BI (spec + data model; Adele
  builds the `.pbix`), plus a cross-platform self-contained Plotly HTML preview.
- **One command:** `python run_etl.py` reproduces the whole pipeline from scratch. The tokenless
  source path works **without any API token**.

## Quick start

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python run_etl.py
```

### Windows (PowerShell)
```powershell
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1   # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -e ".[dev]"
python run_etl.py
```

### Optional: GENESIS API token
The default path needs no token. To use the GENESIS-Online API as the preferred source for recent
years, create a free account at <https://genesis.destatis.de> and set `GENESIS_TOKEN` via a
`.env` file (gitignored):

```
GENESIS_TOKEN=your_token_here
```

- macOS/Linux (one-off): `export GENESIS_TOKEN=…`
- Windows PowerShell (one-off): `$env:GENESIS_TOKEN="…"`

## Definitions & caveats

- **"Fälle" (cases) ≠ unique patients** — one person may be admitted several times.
- Cases are counted at the **hospital's location**, not the patient's place of residence —
  relevant for city-states (Berlin, Hamburg, Bremen) and the Berlin–Brandenburg pair.
- Per-100k figures aggregate by **summing numerator and denominator first, then dividing** —
  rates are never averaged.
- Population has a **series break** after Zensus 2022 (new census basis).

## Licence & attribution

Data © **Statistisches Bundesamt (Destatis)**, licensed under *Datenlizenz Deutschland –
Namensnennung – Version 2.0* (exact table/report citations in `dashboard/DATA_DICTIONARY.md` and
`data/raw/MANIFEST.json`). Geo boundaries © **BKG** (VG2500, dl-de/by-2-0).

## Disclaimer

Independent portfolio project. **Not affiliated with** Destatis or any health authority. No
"best/worst region" rankings — regional differences reflect age structure, cross-state patient
flows, hospital mix and specialisation.
