# Data dictionary — `dashboard/data/`

Star-schema CSVs exported by `python run_etl.py` (Stage 5). UTF-8, `.` decimal separator, one
header row. Fact grain: **Bundesland × year × indicator**. All values trace to Destatis statistic
23111 (see `data/raw/MANIFEST.json`).

> **"Fälle" (cases) ≠ unique patients.** Cases are counted at the hospital's location, not the
> patient's residence. Per-100k figures must aggregate by summing numerator and denominator
> first, then dividing — never average the rates (see `POWERBI_SPEC.md` DAX).

## `dim_bundesland.csv` — 17 rows (16 states + Germany total)
| Column | Type | Description |
|---|---|---|
| `ags_code` | text | AGS key: `01`–`16`; `DG` = Deutschland total. **Relationship key.** |
| `iso_3166_2` | text | ISO code (`DE-BW` …); empty for `DG`. |
| `name_de` | text | German name (`Baden-Württemberg`, `Thüringen`). |
| `name_en` | text | English name. |
| `is_total` | bool | `true` only for the `DG` Germany-total row. |

## `dim_indicator.csv` — one row per indicator
| Column | Type | Description |
|---|---|---|
| `indicator_id` | text | Indicator key (`beds`, `cases`, `beds_per_100k`, …). **Relationship key.** |
| `name_de` / `name_en` | text | Indicator names. |
| `definition_en` | text | Definition (incl. the cases-≠-patients caveat). |
| `unit` | text | `count`, `days`, `persons`, `per_100k`, `percent`. |
| `is_derived` | bool | `true` for recomputed measures. |
| `formula` | text | Formula for derived indicators. |
| `source_table` / `source_url` / `license` | text | Provenance and licence. |

## `dim_year.csv` — one row per year
| Column | Type | Description |
|---|---|---|
| `year` | int | Reporting year (2022–2024). **Relationship key.** |
| `is_anchor` | bool | Headline comparison year. |
| `covid_affected` | bool | `true` for 2020–2022 (case counts depressed/recovering). |
| `population_census_basis` | text | `Zensus 2022` (2022+) or `Zensus 2011` — **series break**. |

## `fact_indicators.csv` — long fact (grain: ags_code × year × indicator)
| Column | Type | Description |
|---|---|---|
| `ags_code` | text | → `dim_bundesland`. |
| `year` | int | → `dim_year`. |
| `indicator_id` | text | → `dim_indicator`. |
| `value` | double | Indicator value (NaN never coerced to 0; special-symbol cells are dropped upstream). |
| `unit` | text | Unit of `value`. |
| `source_id` | text | `destatis_23111_sb_<year>` for source indicators; `derived*` for derived. |

## `fact_indicators_wide.csv` — one row per ags_code × year
Columns: `ags_code`, `year`, `hospitals`, `beds`, `cases`, `bed_days`, `population_avg`,
`beds_per_100k`, `cases_per_100k`, `alos`, `occupancy`. Convenience table; the long
`fact_indicators` is the model's fact.

## `fact_germany_series.csv` — Germany national time series (2000–2024)
One row per year for **Deutschland only**, same measure columns as `fact_indicators_wide`
(`hospitals`, `beds`, `cases`, `bed_days`, `population_avg`, `beds_per_100k`, `cases_per_100k`,
`alos`, `occupancy`). Provides the pandemic context and the pre-COVID 2019 baseline that the
by-Land mart (2022–2024) cannot show. Values are Destatis's published national figures.

## `geo/bundeslaender.topojson`
Simplified state boundaries (BKG **VG2500**, licence dl-de/by-2-0), key **`ags_code`** matching
`dim_bundesland`. For the Power BI Shape Map. WGS84 (EPSG:4326).
