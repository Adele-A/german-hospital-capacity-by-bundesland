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

## 2026-11-09 — Stage 2 source finalisation (verified against downloaded files)

## D6 — Exact source: csv-23111-01 of the Statistischer Bericht XLSX
- **Decision:** parse the machine-readable sheet **`csv-23111-01`** (tidy long format:
  `Gebiet | Wertmerkmal | Jahr | Masseinheit | Wert`) from the Destatis *Statistischer Bericht –
  Grunddaten der Krankenhäuser* XLSX. Each value is keyed by **(Wertmerkmal, Masseinheit)**.
- **Verified URLs (HTTP 200, real XLSX):** 2024 `…247005`, 2023 `…237005`, 2022 `…227005`
  (see `config/sources.yaml` / `MANIFEST.json`). bed_days come as "in 1000" → scaled ×1000.

## D7 — By-Land years = 2022 / 2023 / 2024 (tokenless); 2019 deferred
- **Finding:** `csv-23111-01` carries the 16 Länder **only for the report's own reporting year**;
  earlier years in the sheet are **Deutschland-only**. So each report supplies one by-Land year.
- **Decision:** by-Land analytical years = **2022, 2023, 2024** (three comparable years, all 16
  Länder, one format, tokenless). The Deutschland national series (2000–2024, incl. the pre-COVID
  2019 baseline) is taken from the primary report for pandemic context.
- **2019 by Land deviates from the original plan** (was 2019/2022/2024): the 2019 Fachserie is only
  in the Statistische Bibliothek (currently unreachable here) or GENESIS (needs a token). Adding
  2019–2021 by Land is the **GENESIS-token enhancement** — additive, no rework.

## D8 — 2022 report labelling quirk handled by Land-sum verification
- **Finding:** the 2022 report's `csv-23111-01` has a quirky layout (constant `Jahr=2022`, a
  `Merkmal_1` carrying year-like labels, and a Deutschland row that is actually the prior year).
- **Decision:** rely only on the **16 Land rows** (year := report year) and take the Deutschland
  total from the **primary national series**. Verified: **sum(16 Länder) == Germany total to
  0.0000%** for hospitals/beds/cases/bed-days in every year — so the Land values are correct.

## D5 — Cross-platform
- **Decision:** `pathlib.Path` only, explicit utf-8, Unicode **NFC** normalisation for umlauts
  (with a round-trip test). Wheels-only deps. `.gitattributes eol=lf`. One entry point
  `python run_etl.py`. CI matrix ubuntu/windows/macos × Python 3.14.
