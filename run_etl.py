"""Single entry point for the German hospital capacity ETL.

    python run_etl.py                 # full pipeline (downloads if needed)
    python run_etl.py --skip-download # reuse already-downloaded raw files
    python run_etl.py --years 2019 2022 2023

Stages are filled in across the project stages (extract -> transform -> validate -> export).
The pipeline must run WITHOUT any token on the tokenless source path (see docs/PLAN.md).
"""

from __future__ import annotations

import argparse

from etl import paths

DEFAULT_YEARS = [2019, 2022, 2023]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="German hospital capacity ETL (Destatis).")
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=DEFAULT_YEARS,
        help="Reporting years to include (default: %(default)s).",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Reuse raw files already in data/raw instead of downloading.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    paths.ensure_dirs()
    print(f"[run_etl] years={args.years} skip_download={args.skip_download}")
    # Stages wired in as the project progresses:
    #   1. extract   -> data/raw + MANIFEST.json
    #   2. transform -> DuckDB raw/staging/mart
    #   3. validate  -> reports/validation_report.md
    #   4. export    -> dashboard/data + reports
    print("[run_etl] scaffolding only — stages are added incrementally (see docs/PLAN.md).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
