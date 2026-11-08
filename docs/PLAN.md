# PLAN — German Hospital System by Bundesland (Stage 0)

Independent portfolio project for Adele Amanzhol (GitHub `Adele-A`). Goal: compare hospital
capacity and utilisation across the **16 German federal states (Bundesländer)**, show regional
differences and trends over time, with a focus pair **Berlin–Brandenburg**. Every number must
be traceable to a named source table.

> Status: this plan is the **Stage 0 deliverable**. Nothing is downloaded or built yet. It
> waits for the reviewer's **"ок"** before Stage 1. One decision (GENESIS token) is a hard
> blocker for the preferred data path and needs the user — see **§6 Open questions**.

Stack (verified available): Python 3.14.6, DuckDB, pandas, openpyxl, requests, pandera,
pytest, ruff, plotly. Entry point will be `python run_etl.py`.

---

## 1. Source scouting — what was verified (2026-11-08)

Network and the Destatis APIs were probed live. Findings below are **verified**, not assumed.

### 1.1 Destatis statistics (confirmed real)
| Statistic code | Title | Use |
|---|---|---|
| **23111** | Grunddaten der Krankenhäuser | hospitals, beds, cases, patient-days, occupancy, ALOS |
| **12411** | Fortschreibung des Bevölkerungsstandes | population denominator (per-100k), 65+ share |

Verified: statistic `23111` exists on both GENESIS-Online and the Regionaldatenbank; a concrete
table `23111-0002` ("Personal in Krankenhäusern: Deutschland") resolves on
`genesis.destatis.de`. Statistic `12411` exists on both portals with live, recent years.

### 1.2 The two GENESIS portals — access reality
There are two instances of the Destatis GENESIS database, both running the same `genesisWS`
REST software:

1. **GENESIS-Online — `genesis.destatis.de`** (national DB). Has statistic 23111 **with a
   Bundesland dimension and recent years**. REST API confirmed reachable
   (`.../genesisWS/rest/2020/`, POST + `Accept: application/json`). **Guest access is rejected**
   — a probe with `GAST/GAST` returned `{"Code":15,"Type":"ERROR", ... "access data cannot be
   recognised"}`. ⇒ **A free `GENESIS_TOKEN` is required** for the machine-readable path.
2. **Regionaldatenbank Deutschland — `regionalstatistik.de`** (regional DB). Public web table
   downloads work (`?operation=table&code=...&bypass=true`), **no token**. BUT its **hospital
   tables (23111) only cover up to 2017** — verified table titles:
   - `23111-01-02-4` — Grunddaten der Krankenhäuser, Stichtag 31.12., Kreise (**bis 2003**)
   - `23111-01-04-4` — Krankenhäuser nach Fachabteilungen, Kreise (**ab 2004 bis 2017**)
   ⇒ Regionaldatenbank is **not usable for recent-year hospital data**. Its **population
   tables (12411) are current** and usable tokenless (see §3).

### 1.3 Statistischer Bericht — Grunddaten der Krankenhäuser (XLSX/PDF, tokenless)
Destatis publishes an annual *Statistischer Bericht – Grunddaten der Krankenhäuser* with
Bundesland-level results, downloadable as XLSX/PDF without a token. Confirmed real (e.g. the
2025 Deutschland edition page `...statistischer-bericht-grunddaten-krankenhaeuser-deutschland-2120611257005.html`).
Key notes gathered:
- **From reporting year 2025**, Destatis splits it into a **Deutschland** version and a separate
  **Bundesländer** version (relevant: use the Bundesländer file for state data from 2025 on).
- The older *Fachserie 12 Reihe 6.1.1* series was **discontinued after reporting year 2021**.
- Exact per-year XLSX file URLs are **not yet pinned** (the Destatis publication pages are
  SPA/redirect-heavy); they will be resolved and recorded in `MANIFEST.json` during Stage 2.
  **No file URL will be invented** — if a year's file cannot be located, Stage 2 stops and asks.

### 1.4 Geo boundaries (for the map, used in Stage 5 — not blocking Stage 0)
BKG (Bundesamt für Kartographie und Geodäsie) **VG2500** Verwaltungsgebiete (state level,
license **dl-de/by-2-0**). To be fetched and simplified to TopoJSON in Stage 5; key = AGS state
code. Exact download URL to be confirmed and recorded then.

---

## 2. Recommended sourcing strategy

**Preferred (machine-readable, reproducible, updatable) — needs token:**
- Hospital data: **GENESIS-Online API, statistic 23111**, Bundesland × year, via `GENESIS_TOKEN`.
  The exact national-DB table code(s) carrying beds/cases/patient-days by Land will be selected
  from the live catalogue (`catalogue/tables?selection=23111*`) once the token is available, and
  recorded in `config/sources.yaml` + `MANIFEST.json`. (Guest catalogue access is blocked, so
  the final code list cannot honestly be fixed before the token exists.)
- Population: **GENESIS-Online API, statistic 12411**, Durchschnittsbevölkerung by Land (see §3).
- Cross-check / fallback: the **Statistischer Bericht XLSX** for the same years.

**Tokenless fallback (if the user prefers not to register):**
- Hospital data: **Statistischer Bericht – Grunddaten der Krankenhäuser (XLSX)** per year,
  Bundesland-level, downloaded by HTTP. More fragile (per-year layout differs; careful cell
  parsing + validation needed) but fully traceable and reproducible.
- Population: **Regionaldatenbank 12411** (`bypass=true`, tokenless), mid-year 30.06 as the
  annual-average proxy (see §3).

Both paths produce the **same star schema and the same README numbers**; only the extract layer
differs. Recommendation: **ask the user for a free GENESIS token** (5-minute registration) to
take the preferred path; keep the XLSX path implemented as the documented fallback + sverka.

---

## 3. Population denominator (per-100k) — decision needed

Per-100k indicators must divide by a single, documented population figure. Rule (per spec): when
aggregating several states, **sum numerator and denominator first, then divide — never average
rates**.

| Option | Source | Pros | Cons |
|---|---|---|---|
| **A. Durchschnittsbevölkerung (annual average)** — *recommended* | GENESIS 12411 (token) | matches Destatis's own "je 100 000" methodology; most correct for flows during the year | needs token |
| B. Mid-year 30.06. population | Regionaldatenbank `12411-06-01-4` (tokenless) | good proxy for annual average; no token | not identical to Destatis average |
| C. Year-end 31.12. population | Regionaldatenbank `12411-01-01-4` (tokenless) | simplest | biased vs. during-year activity |

**Recommendation: Option A** (annual average) when a token is available, else **Option B**
(mid-year) as the tokenless proxy, with the choice recorded in metadata per indicator.

⚠️ **Series break (must be described):** population from the reporting period after **Zensus
2022** is based on the new census; earlier years on Zensus 2011. This creates a discontinuity in
per-100k series across the 2022 boundary — flagged in validation and described in the memo/README.
Population year = hospital-data year.

---

## 4. Indicators (unit of observation: Bundesland × year)

| indicator_id | name_de | name_en | unit | type |
|---|---|---|---|---|
| `population_avg` | Durchschnittliche Bevölkerung | Average population | persons | source |
| `hospitals` | Krankenhäuser | Hospitals | count | source |
| `beds` | Aufgestellte Betten (Jahresdurchschnitt) | Available beds (annual avg) | count | source |
| `cases` | Fallzahl (stationäre Behandlungsfälle) | Inpatient cases | count | source |
| `bed_days` | Berechnungs- und Belegungstage | Patient-days | days | source (if available) |
| `alos` | Durchschnittliche Verweildauer | Average length of stay | days | source + recomputed |
| `occupancy` | Durchschnittliche Bettenauslastung | Bed occupancy rate | % | source + recomputed |
| `beds_per_100k` | Betten je 100 000 Einwohner | Beds per 100k | per 100k | derived |
| `cases_per_100k` | Fälle je 100 000 Einwohner | Cases per 100k | per 100k | derived |

Optional later: staff (ärztliches Personal / Pflegedienst in Vollkräften), beds by ownership
type (öffentlich / freigemeinnützig / privat).

**Definitions / traps carried into every visual + README:**
- **"Fälle" (cases) ≠ unique patients** — one person may be admitted several times.
- Derived recompute: `alos = bed_days / cases`; `occupancy = bed_days / (beds × days_in_year) × 100`
  (leap years handled). Recomputed vs. published values compared within tolerance → validation report.
- Destatis **special symbols** (`-` nil, `.`/`...` unknown, `x` not applicable, `/` not
  publishable for confidentiality) are **never silently coerced to 0** — legend verified per source.
- Each indicator stores: source (table code / report, URL), definition (de + en), unit, year,
  download date, license → `dim_indicator`.

### Years
Target **≥3 comparable years: 2019 (pre-COVID), 2022 (COVID-affected), latest available
(2023, or 2024 if published)**. A continuous series within one consistent definition if feasible.
Must describe: COVID effect on 2020–2021 cases, the Zensus-2022 population break, and any
Krankenhausstatistik methodology changes. Final year list confirmed once the source is fixed.

---

## 5. Repository structure (target)

```
├── README.md
├── pyproject.toml / requirements.txt
├── run_etl.py                      # extract → transform → validate → export
├── config/
│   ├── sources.yaml                # table codes / report URLs, years, params
│   └── bundeslaender.csv           # 16-state reference (AGS, ISO, name_de/en, spellings)
├── etl/ (extract/ transform/ validate/ export/)
├── sql/                            # staging_*.sql, mart_*.sql, checks_*.sql
├── data/raw/ · data/warehouse/     # .gitignore except data/raw/MANIFEST.json
├── dashboard/ (data/ geo/ POWERBI_SPEC.md DATA_DICTIONARY.md screenshots/)
├── reports/ (validation_report.md analytical_memo.md figures/ dashboard_preview.html)
├── docs/ (PLAN.md decisions.md UPDATE_PROCEDURE.md)
└── tests/ (fixtures/ + unit tests, no network)
```

DuckDB warehouse `data/warehouse/hospitals.duckdb`, layers `raw → staging → mart`. Mart = long
`fact_indicators (ags_code, year, indicator_id, value, unit, source_id)` + a wide version.
Cross-platform: `pathlib.Path`, explicit utf-8, Unicode **NFC** for umlauts (+ round-trip test),
wheels-only deps, `.gitattributes eol=lf`, `lower_snake_case`. CI matrix ubuntu/windows/macos ×
py3.14 (ruff + pytest on small synthetic fixtures, no GENESIS calls).

---

## 6. Open questions (need the user, via parent session)

1. **GENESIS token (blocker for the preferred path).** Guest access is verified blocked. Will
   the user register a free GENESIS-Online account (`genesis.destatis.de`) and provide the token
   via `.env` → `GENESIS_TOKEN=…` (gitignored)? **If yes** → preferred machine-readable path
   (§2). **If no** → tokenless XLSX + Regionaldatenbank-population path (§2 fallback), which is
   viable but relies on per-year XLSX parsing.
2. **Years:** confirm **2019 / 2022 / latest (2023 or 2024)**. OK to adjust once availability is
   checked against the chosen source.
3. **Population denominator:** confirm **Durchschnittsbevölkerung (annual average)** (Option A,
   token) or the **mid-year 30.06** tokenless proxy (Option B).

Default if no objection: pursue the **preferred path pending the token**; implement the tokenless
XLSX fallback regardless so the pipeline runs end-to-end either way; years **2019/2022/2023**;
denominator **annual average (A), mid-year (B) as fallback**.

---

## 7. Honesty guardrails (restated)
Independent portfolio project; no Destatis/government logos; no "best/worst region" ratings;
every number traceable to a named source table; table codes, URLs and values are **verified or
left open**, never invented — if a source/file is unreachable, stop and ask.
