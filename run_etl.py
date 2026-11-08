"""Single entry point for the German hospital capacity ETL.

    python run_etl.py                 # full pipeline (downloads if needed)
    python run_etl.py --skip-download # reuse already-downloaded raw files
    python run_etl.py --years 2019 2022 2023

Stages are filled in across the project stages (extract -> transform -> validate -> export).
The pipeline must run WITHOUT any token on the tokenless source path (see docs/PLAN.md).
"""

from __future__ import annotations

import argparse

from etl import config, extract, paths, warehouse


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="German hospital capacity ETL (Destatis).")
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=config.years(),
        help="By-Land reporting years to include (default from config/sources.yaml).",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Reuse raw files already in data/raw instead of downloading.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download raw files even if present.",
    )
    return parser.parse_args(argv)


def stage_extract(*, skip_download: bool, force_download: bool) -> None:
    """Stage 2 — download reports (idempotent) and load the raw parsed layer into DuckDB."""
    if skip_download:
        print("[extract] --skip-download: reusing data/raw and refreshing MANIFEST")
    manifest = extract.download_reports(force=force_download)
    for m in manifest:
        print(f"[extract] {m['action']:>10}  {m['filename']}  ({m['size_bytes'] // 1024} KiB)")

    raw = extract.extract_all()
    con = warehouse.connect()
    try:
        n = warehouse.write_table(con, "raw_source_long", raw)
    finally:
        con.close()
    print(f"[extract] raw_source_long: {n} rows loaded into {paths.DUCKDB_PATH.name}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    paths.ensure_dirs()
    print(f"[run_etl] by-Land years={args.years}")
    stage_extract(skip_download=args.skip_download, force_download=args.force_download)
    # Later stages (transform -> validate -> export) are wired in as the project progresses.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
