"""Stage 1 — Bundesland reference and name normalisation.

Network-free: exercises only the local reference CSV so CI stays green without any source API.
"""

import unicodedata

import pytest

from etl import bundeslaender as bl


def test_sixteen_states_plus_total():
    ref = bl.load_reference()
    states = [b for b in ref if not b.is_total]
    totals = [b for b in ref if b.is_total]
    assert len(states) == 16
    assert len(totals) == 1
    assert {b.ags_code for b in states} == {f"{i:02d}" for i in range(1, 17)}
    assert totals[0].ags_code == bl.GERMANY_TOTAL_CODE


def test_iso_codes_unique_and_well_formed():
    states = [b for b in bl.load_reference() if not b.is_total]
    isos = [b.iso_3166_2 for b in states]
    assert len(set(isos)) == 16
    assert all(iso.startswith("DE-") and len(iso) == 5 for iso in isos)


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Schleswig-Holstein", "01"),
        ("Hamburg", "02"),
        ("Freie und Hansestadt Hamburg", "02"),
        ("Niedersachsen", "03"),
        ("Lower Saxony", "03"),
        ("Nordrhein-Westfalen", "05"),
        ("NRW", "05"),
        ("Baden-Württemberg", "08"),
        ("Baden-Wuerttemberg", "08"),  # ue transliteration
        ("BADEN-WÜRTTEMBERG", "08"),  # case-insensitive
        ("Bayern", "09"),
        ("Freistaat Bayern", "09"),
        ("Berlin", "11"),
        ("Brandenburg", "12"),
        ("Mecklenburg-Vorpommern", "13"),
        ("Thüringen", "16"),
        ("Thueringen", "16"),  # ue transliteration
        ("  Thüringen  ", "16"),  # surrounding whitespace
    ],
)
def test_normalize_known_names(name, expected):
    assert bl.normalize_name(name) == expected


@pytest.mark.parametrize("total_name", ["Insgesamt", "Deutschland", "Bundesgebiet", "Germany"])
def test_total_aliases_resolve(total_name):
    code = bl.normalize_name(total_name)
    assert code == bl.GERMANY_TOTAL_CODE
    assert bl.is_total(code)


@pytest.mark.parametrize("bad", ["Atlantis", "Bayern-Nord", "", "Saxon"])
def test_unknown_names_raise(bad):
    with pytest.raises(KeyError):
        bl.normalize_name(bad)


def test_umlaut_round_trip_nfc(tmp_path):
    """Write umlaut names as UTF-8, read them back, confirm byte round-trip + NFC matching."""
    names = ["Baden-Württemberg", "Thüringen"]
    f = tmp_path / "umlaut.txt"
    f.write_text("\n".join(names), encoding="utf-8")
    read_back = f.read_text(encoding="utf-8").splitlines()
    assert read_back == names
    for n in names:
        assert bl.normalize_name(n) == bl.normalize_name(bl.nfc(n))


def test_nfd_input_resolves_like_nfc():
    """macOS may deliver decomposed (NFD) strings; they must still resolve."""
    nfd = unicodedata.normalize("NFD", "Thüringen")
    assert nfd != "Thüringen"  # genuinely decomposed
    assert bl.normalize_name(nfd) == "16"


def test_state_codes_helper():
    assert bl.state_codes() == [f"{i:02d}" for i in range(1, 17)]
    assert bl.GERMANY_TOTAL_CODE in bl.state_codes(include_total=True)
