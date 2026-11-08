"""Stage 2 — report parsing (network-free, synthetic rows mirroring csv-23111-01)."""

import math

from etl import config
from etl.config import Report
from etl.extract import rows_to_records

REP = Report(
    key="test",
    role="primary",
    report_year=2024,
    series_sheet="csv-23111-01",
    filename="unused.xlsx",
    url="about:blank",
)

HEADER = [
    "Statistik_Code",
    "Statistik_Name",
    "Gebiet",
    "Wertmerkmal",
    "Jahr",
    "Masseinheit",
    "Wert",
]
BODY = [
    ["23111", "Grunddaten", "Berlin ", "Krankenhäuser insgesamt", "2024", "Anzahl", "88"],
    # bed_days are reported "in 1000" -> scaled x1000; German decimal comma
    [
        "23111",
        "Grunddaten",
        "Berlin ",
        "Patientenbewegung Berechnungs-/ Belegungstage",
        "2024",
        "in 1000",
        "5.483,52",
    ],
    # special symbol must NOT become 0
    ["23111", "Grunddaten", "Thüringen", "Patientenbewegung Fallzahl", "2024", "Anzahl", "-"],
    # non-region Gebiet -> skipped
    ["23111", "Grunddaten", "Irgendwas", "Krankenhäuser insgesamt", "2024", "Anzahl", "5"],
    # unmatched (Wertmerkmal, Masseinheit) -> skipped (this is the yoy% variant)
    [
        "23111",
        "Grunddaten",
        "Berlin",
        "Krankenhäuser insgesamt",
        "2024",
        "Veränderung zum Vorjahr (in %)",
        "1,2",
    ],
]


def _records():
    return {(_r["ags_code"], _r["indicator_id"]): _r for _r in rows_to_records(HEADER, BODY, REP)}


def test_known_indicators_parsed_and_normalised():
    recs = _records()
    assert recs[("11", "hospitals")]["value"] == 88.0
    assert recs[("11", "hospitals")]["flag"] == "ok"


def test_bed_days_scaled_to_days():
    recs = _records()
    r = recs[("11", "bed_days")]
    assert r["value"] == 5483.52 * 1000  # "in 1000" -> days
    assert r["unit"] == "days"


def test_special_symbol_is_nan_not_zero():
    recs = _records()
    r = recs[("16", "cases")]
    assert math.isnan(r["value"])
    assert r["flag"] == "nil"


def test_non_region_and_unmatched_rows_dropped():
    keys = _records().keys()
    # only Berlin(11) + Thüringen(16) survive; "Irgendwas" and the %-variant are dropped
    assert {k[0] for k in keys} == {"11", "16"}
    assert all(k[1] != "occupancy_published" for k in keys)


def test_config_indicator_keys_unique():
    keys = [(si.wertmerkmal, si.masseinheit) for si in config.source_indicators()]
    assert len(keys) == len(set(keys))
