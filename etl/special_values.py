"""Parse Destatis cell values, honouring the special symbols.

Destatis marks cells with symbols that each carry a distinct meaning; coercing them to 0 would
be a data-integrity error. We map every non-numeric cell to NaN plus a machine-readable flag,
and parse German-formatted numbers (``1.234,5`` -> ``1234.5``) correctly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# symbol -> short flag code (meanings documented in config/sources.yaml::special_symbols)
SPECIAL_FLAGS: dict[str, str] = {
    "-": "nil",  # genuine zero / nothing to report
    ".": "no_data",  # no data / not available
    "...": "no_data",
    "…": "no_data",
    "x": "not_applicable",
    "/": "not_reliable",
}


@dataclass(frozen=True)
class ParsedValue:
    value: float  # NaN when not a real number
    flag: str  # "ok", or one of the SPECIAL_FLAGS codes, or "unparsable"


def _to_number(text: str) -> float | None:
    """Parse a German- or English-formatted number, or return None."""
    s = text.strip().replace("\xa0", "").replace(" ", "")
    if not s:
        return None
    if "," in s and "." in s:
        # German grouping: "1.234.567,8" -> "1234567.8"
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        # decimal comma only: "12,5" -> "12.5"
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_value(raw: object) -> ParsedValue:
    """Parse one source cell into a (value, flag) pair."""
    if raw is None:
        return ParsedValue(math.nan, "no_data")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        v = float(raw)
        return ParsedValue(v, "ok") if not math.isnan(v) else ParsedValue(math.nan, "no_data")

    text = str(raw).strip()
    if text in SPECIAL_FLAGS:
        return ParsedValue(math.nan, SPECIAL_FLAGS[text])

    num = _to_number(text)
    if num is None:
        return ParsedValue(math.nan, "unparsable")
    return ParsedValue(num, "ok")
