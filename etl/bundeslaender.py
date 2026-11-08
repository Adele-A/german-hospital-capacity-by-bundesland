"""Reference data and name normalisation for the 16 German federal states (Bundesländer).

Any state name encountered in a Destatis source — with umlauts (``Thüringen``), the ``ue``/``ü``
transliteration (``Thueringen``), parenthetical additions (``Freie und Hansestadt Hamburg``),
or the country total (``Insgesamt`` / ``Deutschland``) — must resolve to exactly one AGS code.
Unknown values raise, so a silent mismatch can never slip into the mart.

Matching is accent- and case-insensitive via a canonical key: NFC normalise, casefold,
transliterate German umlauts (ä→ae, ö→oe, ü→ue, ß→ss), and collapse whitespace/hyphen spacing.
This makes ``ü``/``ue`` spellings collapse automatically, on top of the explicit alias list.
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from etl.paths import BUNDESLAENDER_CSV

GERMANY_TOTAL_CODE = "DG"

_UMLAUT_MAP = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "ae",
        "Ö": "oe",
        "Ü": "ue",
        "ß": "ss",
    }
)


@dataclass(frozen=True)
class Bundesland:
    ags_code: str
    iso_3166_2: str
    name_de: str
    name_en: str
    is_total: bool


def nfc(text: str) -> str:
    """Normalise to Unicode NFC (macOS may hand back NFD file/data strings)."""
    return unicodedata.normalize("NFC", text)


def canonical_key(name: str) -> str:
    """Accent/case-insensitive lookup key used for name matching."""
    key = nfc(name).strip().casefold().translate(_UMLAUT_MAP)
    # normalise whitespace and hyphen spacing: "Baden - Wuerttemberg" -> "baden-wuerttemberg"
    key = " ".join(key.split())
    key = "-".join(part.strip() for part in key.split("-"))
    return key


@lru_cache(maxsize=1)
def load_reference(csv_path: Path | None = None) -> tuple[Bundesland, ...]:
    """Load the 16 states plus the Germany-total row from the reference CSV."""
    path = csv_path or BUNDESLAENDER_CSV
    rows: list[Bundesland] = []
    with path.open(encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh):
            rows.append(
                Bundesland(
                    ags_code=raw["ags_code"].strip(),
                    iso_3166_2=raw["iso_3166_2"].strip(),
                    name_de=nfc(raw["name_de"].strip()),
                    name_en=nfc(raw["name_en"].strip()),
                    is_total=raw["is_total"].strip().lower() == "true",
                )
            )
    return tuple(rows)


@lru_cache(maxsize=1)
def _lookup(csv_path: Path | None = None) -> dict[str, str]:
    """Map every canonical key (names + aliases) to an AGS code; fail on collisions."""
    table: dict[str, str] = {}
    path = csv_path or BUNDESLAENDER_CSV

    def add(key_source: str, code: str) -> None:
        key = canonical_key(key_source)
        if not key:
            return
        if key in table and table[key] != code:
            raise ValueError(
                f"Ambiguous Bundesland alias {key_source!r}: maps to both {table[key]} and {code}."
            )
        table[key] = code

    with path.open(encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh):
            code = raw["ags_code"].strip()
            add(raw["name_de"], code)
            add(raw["name_en"], code)
            add(code, code)  # the code itself resolves to itself
            for alias in raw.get("aliases", "").split("|"):
                if alias.strip():
                    add(alias, code)
    return table


def normalize_name(name: str, *, csv_path: Path | None = None) -> str:
    """Resolve a source state name to its AGS code. Raises KeyError on an unknown name."""
    if name is None:
        raise KeyError("Bundesland name is None")
    key = canonical_key(str(name))
    try:
        return _lookup(csv_path)[key]
    except KeyError as exc:
        raise KeyError(
            f"Unknown Bundesland name {name!r} (canonical key {key!r}); "
            f"add it to config/bundeslaender.csv aliases if it is a real source spelling."
        ) from exc


def is_total(ags_code: str) -> bool:
    """True for the Germany-total row."""
    return ags_code.strip().upper() == GERMANY_TOTAL_CODE


def state_codes(*, include_total: bool = False) -> list[str]:
    """The AGS codes, 01–16 (optionally plus the Germany total)."""
    return [b.ags_code for b in load_reference() if include_total or not b.is_total]
