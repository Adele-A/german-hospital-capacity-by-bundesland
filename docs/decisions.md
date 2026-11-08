# Decisions log

Durable record of methodological and engineering decisions. Each entry: decision, date,
rationale. See `docs/PLAN.md` for the full Stage 0 source scouting.

## 2026-11-08 — Stage 0 plan approved
Plan reviewed and approved. Methodological defaults accepted.

## D1 — Data sourcing: tokenless path is the primary, reproducible baseline
- **Decision:** `python run_etl.py` must run **without any token**. The primary, always-working
  source is the Destatis **Statistischer Bericht – Grunddaten der Krankenhäuser** (XLSX, by
  Bundesland) for hospital indicators, plus **statistic 12411** population from the
  Regionaldatenbank (`regionalstatistik.de`, public `bypass=true`).
- **Rationale:** GENESIS-Online guest access is blocked (verified: `GAST/GAST` → `Code 15`); a
  free `GENESIS_TOKEN` cannot be assumed to exist. The Regionaldatenbank hospital tables stop at
  2017, so they cannot supply recent years — the XLSX reports can.
- **If a `GENESIS_TOKEN` is later provided:** the GENESIS-Online API (statistic 23111) becomes
  the *preferred* source for recent years; the tokenless path stays as a documented fallback and
  cross-check. This is additive — no rework of the star schema.

## D2 — Years: 2019 / 2022 / latest full Bundesländer year
- **Decision:** 2019 (pre-COVID), 2022 (COVID-affected), and the latest **complete**
  Bundesland-level year (2023; use 2024 only if the full Bundesländer report is published).
- **Rationale:** three comparable years spanning the pandemic; never include a partial year.

## D3 — Per-100k denominator: annual average, mid-year fallback
- **Decision:** `population_avg` = **Durchschnittsbevölkerung** (annual average) when available;
  **mid-year 30.06.** population (Regionaldatenbank `12411-06-01-4`) as the tokenless proxy.
- **Rationale:** annual average matches Destatis's own "je 100 000" methodology. Aggregation
  across states always sums numerator and denominator first, then divides — never averages rates.
- **Series break:** population from the reporting period after **Zensus 2022** uses the new
  census; earlier years use Zensus 2011. Flagged in validation and described in memo/README.

## D4 — Raw files not committed; provenance in MANIFEST.json
- **Decision:** `data/` is gitignored except `data/raw/MANIFEST.json` (source URL / table code,
  download timestamp, sha256, license). Download is idempotent.

## D5 — Cross-platform
- **Decision:** `pathlib.Path` only, explicit utf-8, Unicode **NFC** normalisation for umlauts
  (with a round-trip test). Wheels-only deps. `.gitattributes eol=lf`. One entry point
  `python run_etl.py`. CI matrix ubuntu/windows/macos × Python 3.14.
