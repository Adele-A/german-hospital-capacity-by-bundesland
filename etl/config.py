"""Load and expose the source configuration (config/sources.yaml)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from etl.paths import SOURCES_YAML


@dataclass(frozen=True)
class Report:
    key: str
    role: str
    report_year: int
    series_sheet: str
    filename: str
    url: str


@dataclass(frozen=True)
class SourceIndicator:
    id: str
    wertmerkmal: str
    masseinheit: str
    unit: str
    scale: float


@lru_cache(maxsize=1)
def load_config(path: Path | None = None) -> dict:
    with (path or SOURCES_YAML).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def reports() -> list[Report]:
    cfg = load_config()
    return [
        Report(
            key=k,
            role=r["role"],
            report_year=int(r["report_year"]),
            series_sheet=r["series_sheet"],
            filename=r["filename"],
            url=r["url"],
        )
        for k, r in cfg["reports"].items()
    ]


def primary_report() -> Report:
    return next(r for r in reports() if r.role == "primary")


def source_indicators() -> list[SourceIndicator]:
    cfg = load_config()
    return [SourceIndicator(**si) for si in cfg["source_indicators"]]


def years() -> list[int]:
    return [int(y) for y in load_config()["years"]]


def anchor_years() -> list[int]:
    return [int(y) for y in load_config()["anchor_years"]]


def license_info() -> dict:
    return load_config()["license"]


def special_symbols() -> dict[str, str]:
    return load_config()["special_symbols"]
