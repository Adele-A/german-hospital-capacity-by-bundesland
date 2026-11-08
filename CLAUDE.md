# CLAUDE.md — German Hospital System by Bundesland (Destatis)

**Authoritative task spec:** `../init-prompts/02_german_hospital_system_bundeslaender.md`.
Read it in full and follow it. This file holds the durable guardrails only.

Independent portfolio project for Adele Amanzhol (GitHub `Adele-A`). Stack: Python 3.14,
DuckDB, Power BI. Entry point: `python run_etl.py`. Value = correctness and traceability of
every number back to its source table.

## Guardrails (always)
- **Language:** talk to the user in Russian; all repo content in English. Keep German
  indicator names in metadata (`name_de`, `name_en`).
- **Honesty:** independent portfolio project; no "best/worst region" ratings; every number
  traceable to a source table; never fabricate table codes / URLs / values — stop and ask.
- **Stop at Stage 0:** source scouting + `docs/PLAN.md` (GENESIS table codes, chosen years,
  population denominator), show it, wait for "ок".
- **Git:** stage-by-stage commits after tests; `git init` if needed (branch `main`);
  **never push without explicit confirmation.**
- **Data & secrets:** `data/` gitignored except `MANIFEST.json`; download idempotent;
  `GENESIS_TOKEN` via `.env` (gitignored) — never commit it; stop if GENESIS is unreachable.
- **Cross-platform (Win+macOS):** `pathlib.Path`; explicit utf-8 + Unicode `NFC` for umlauts
  (test umlaut round-trips); wheels-only deps; `.gitattributes eol=lf`; `lower_snake_case`;
  CI matrix ubuntu/windows/macos on fixtures (no GENESIS calls).
- **Power BI:** prepare star-schema CSVs + TopoJSON + DAX + `POWERBI_SPEC.md` only; Adele
  builds `.pbix`; also emit a self-contained Plotly `reports/dashboard_preview.html`.

## Project-specific traps (see spec §2–3)
- "Fälle" (cases) ≠ unique patients — state it in definitions, visuals, README.
- Destatis special symbols (`-`, `.`, `x`, `/`, `…`) each have a meaning — never silently
  coerce to 0.
- Per-100k aggregation: sum numerator and denominator first, then divide — never average rates.
- Series breaks: population after Zensus 2022; COVID effect on 2020–2021 cases — describe both.

## Environment
Use the installed Python 3.14 — numpy/pandas/duckdb/shapely/pyogrio/pyproj have 3.14 wheels,
geopandas/pandera are pure-Python (verified). GENESIS-Online API may need a free token. Full
preflight: `../init-prompts/ENVIRONMENT.md`.
