"""Stage 2 — Destatis special-symbol and number parsing."""

import math

import pytest

from etl.special_values import parse_value


@pytest.mark.parametrize(
    "symbol,flag",
    [
        ("-", "nil"),
        (".", "no_data"),
        ("...", "no_data"),
        ("…", "no_data"),
        ("x", "not_applicable"),
        ("/", "not_reliable"),
    ],
)
def test_special_symbols_become_nan_with_flag(symbol, flag):
    pv = parse_value(symbol)
    assert math.isnan(pv.value)
    assert pv.flag == flag  # never silently 0


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("88", 88.0),
        # Destatis csv-* sheets use point-decimals with no thousands grouping:
        ("748434.5", 748434.5),
        ("545.0760717066852", 545.0760717066852),  # plain float
        (5483.52, 5483.52),  # already numeric
        # German-formatted numbers are still handled defensively (comma present -> German):
        ("1.234.567,8", 1234567.8),  # grouping dots + decimal comma
        ("12,5", 12.5),  # decimal comma only
    ],
)
def test_number_parsing(raw, expected):
    pv = parse_value(raw)
    assert pv.flag == "ok"
    assert pv.value == pytest.approx(expected)


def test_unparsable_flagged():
    pv = parse_value("not a number")
    assert math.isnan(pv.value)
    assert pv.flag == "unparsable"


def test_none_is_no_data():
    assert parse_value(None).flag == "no_data"
