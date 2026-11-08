# Power BI specification — German hospital capacity by Bundesland

Step-by-step build guide for the `.pbix`. Claude prepares the data model, measures and this spec;
**Adele builds the dashboard** (Power BI Desktop is Windows-only — on macOS use a Windows VM or
a Windows PC). Inputs are the CSVs in `dashboard/data/` and the TopoJSON in `dashboard/geo/`.

> **Honesty:** the dashboard is not built yet — `dashboard/screenshots/` is empty until Adele
> adds captures. A cross-platform preview of the same content is in
> `reports/dashboard_preview.html`.

## 1. Import

1. **Get Data → Text/CSV** for each file in `dashboard/data/`:
   `dim_bundesland`, `dim_indicator`, `dim_year`, `fact_indicators`, `fact_indicators_wide`.
   Set the locale to **English (United States)** so `.` is read as the decimal separator.
2. Confirm types: `value`, `beds_per_100k`, `alos`, `occupancy` = Decimal; `year` = Whole Number;
   keys (`ags_code`, `indicator_id`) = Text.
3. **Shape Map geography:** `dashboard/geo/bundeslaender.topojson`, key property `ags_code`.

## 2. Model (relationships)

Star schema — single-direction relationships from dimensions to the fact:

| From (1) | To (\*) | Key |
|---|---|---|
| `dim_bundesland[ags_code]` | `fact_indicators[ags_code]` | `ags_code` |
| `dim_indicator[indicator_id]` | `fact_indicators[indicator_id]` | `indicator_id` |
| `dim_year[year]` | `fact_indicators[year]` | `year` |

Keep `fact_indicators` (long) as the model fact. `fact_indicators_wide` is optional, for quick
table visuals. Hide the raw key columns on the fact.

## 3. DAX measures

The fact is long, so a measure selects its indicator by `indicator_id`. **Per-100k must aggregate
by summing numerator and denominator first, then dividing — never average the per-Land rates.**

```DAX
-- generic value selector (sum works because one indicator is picked per visual via a slicer/filter)
Value = SUM ( fact_indicators[value] )

-- pull a specific indicator regardless of the current indicator filter
Beds       = CALCULATE ( SUM ( fact_indicators[value] ), fact_indicators[indicator_id] = "beds" )
Cases      = CALCULATE ( SUM ( fact_indicators[value] ), fact_indicators[indicator_id] = "cases" )
Hospitals  = CALCULATE ( SUM ( fact_indicators[value] ), fact_indicators[indicator_id] = "hospitals" )
Bed Days   = CALCULATE ( SUM ( fact_indicators[value] ), fact_indicators[indicator_id] = "bed_days" )
Population = CALCULATE ( SUM ( fact_indicators[value] ), fact_indicators[indicator_id] = "population_avg" )

-- correct aggregation: sum numerator & denominator across the selection, THEN divide
Beds per 100k  = DIVIDE ( [Beds]  * 100000, [Population] )
Cases per 100k = DIVIDE ( [Cases] * 100000, [Population] )

-- utilisation (also numerator/denominator, never an average of rates)
ALOS (days)     = DIVIDE ( [Bed Days], [Cases] )
Occupancy (%)   =
VAR DaysInYear =
    SUMX ( VALUES ( dim_year[year] ),
        IF ( MOD ( dim_year[year], 4 ) = 0 && ( MOD ( dim_year[year], 100 ) <> 0 || MOD ( dim_year[year], 400 ) = 0 ), 366, 365 ) )
RETURN DIVIDE ( [Bed Days], [Beds] * DaysInYear ) * 100

-- deviation of a state's per-100k from the Germany-wide rate (for the comparison page)
Beds per 100k (DE)  =
    CALCULATE ( [Beds per 100k], REMOVEFILTERS ( dim_bundesland ), dim_bundesland[is_total] = FALSE )
Beds per 100k vs DE = [Beds per 100k] - [Beds per 100k (DE)]
```

Exclude the Germany total (`dim_bundesland[is_total] = TRUE`, `ags_code = "DG"`) from state
rankings and the map; use it only for the national reference line.

## 4. Pages

1. **Overview / Map** — Shape Map of states (`ags_code`); field = selected indicator; slicers for
   indicator and year. Cards for national totals.
2. **Bundesland comparison** — bar chart ranking states on `[Beds per 100k]` (or chosen measure),
   with `[… vs DE]` showing deviation from the German average.
3. **Trends** — line chart by year; small multiples (one mini-line per state).
4. **Berlin–Brandenburg** — the two states side by side plus their combined figure, with a note
   that cases are counted at the **hospital's location**, not patient residence (cross-state
   patient flows between Berlin and Brandenburg).
5. **Definitions & sources** — table from `dim_indicator` (name_de/name_en, definition, unit,
   formula, source, licence) and the Destatis/BKG attribution + disclaimer.

## 5. Formatting notes

- Title each per-100k visual "per 100,000 inhabitants"; note the **Zensus 2022 series break**
  (population basis changes from 2022) wherever years are compared.
- Caption the cases visuals: **"Fälle" (cases) ≠ unique patients.**
- No "best/worst region" language — differences reflect age structure, patient flows, and
  hospital mix.
