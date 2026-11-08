"""Indicator metadata (dim_indicator) and the derived-indicator definitions.

Keeps German + English names next to each other, records the source table / URL / licence, and
states the formula for every derived measure. Consumed by the transform stage and the exports.
"""

from __future__ import annotations

SOURCE_TABLE = (
    "Destatis 23111 — Grunddaten der Krankenhäuser, Statistischer Bericht, sheet csv-23111-01"
)
SOURCE_URL = "https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Gesundheit/Krankenhauser/Publikationen/_publikationen-innen-grunddaten-krankenhaus.html"
LICENSE = "Datenlizenz Deutschland – Namensnennung – Version 2.0"

# dim_indicator rows. `is_derived` marks measures recomputed in the mart; `formula` documents how.
INDICATORS: list[dict] = [
    # --- source indicators (as published by Destatis) ---
    {
        "indicator_id": "hospitals",
        "name_de": "Krankenhäuser",
        "name_en": "Hospitals",
        "definition_en": "Number of hospitals at location, as of 31 Dec.",
        "unit": "count",
        "is_derived": False,
        "formula": "",
    },
    {
        "indicator_id": "beds",
        "name_de": "Aufgestellte Betten",
        "name_en": "Available beds",
        "definition_en": "Beds set up (annual average).",
        "unit": "count",
        "is_derived": False,
        "formula": "",
    },
    {
        "indicator_id": "cases",
        "name_de": "Fallzahl (stationäre Behandlungsfälle)",
        "name_en": "Inpatient cases",
        "definition_en": "Inpatient treatment cases — counted at the hospital's location, NOT "
        "unique patients (one person may be admitted several times).",
        "unit": "count",
        "is_derived": False,
        "formula": "",
    },
    {
        "indicator_id": "bed_days",
        "name_de": "Berechnungs- und Belegungstage",
        "name_en": "Patient-days",
        "definition_en": "Billing/occupancy days in the year.",
        "unit": "days",
        "is_derived": False,
        "formula": "",
    },
    # --- derived indicators (recomputed in the mart) ---
    {
        "indicator_id": "population_avg",
        "name_de": "Durchschnittliche Bevölkerung",
        "name_en": "Average population",
        "definition_en": "Annual-average population (Durchschnittsbevölkerung) recovered from the "
        "Destatis-published per-100k rates; equals the denominator Destatis used.",
        "unit": "persons",
        "is_derived": True,
        "formula": "beds / beds_per_100k_published * 100000 (cross-checked vs cases-based)",
    },
    {
        "indicator_id": "beds_per_100k",
        "name_de": "Betten je 100 000 Einwohner",
        "name_en": "Beds per 100k population",
        "definition_en": "Available beds per 100,000 inhabitants.",
        "unit": "per_100k",
        "is_derived": True,
        "formula": "beds / population_avg * 100000",
    },
    {
        "indicator_id": "cases_per_100k",
        "name_de": "Fälle je 100 000 Einwohner",
        "name_en": "Cases per 100k population",
        "definition_en": "Inpatient cases per 100,000 inhabitants.",
        "unit": "per_100k",
        "is_derived": True,
        "formula": "cases / population_avg * 100000",
    },
    {
        "indicator_id": "alos",
        "name_de": "Durchschnittliche Verweildauer",
        "name_en": "Average length of stay",
        "definition_en": "Mean inpatient length of stay in days.",
        "unit": "days",
        "is_derived": True,
        "formula": "bed_days / cases",
    },
    {
        "indicator_id": "occupancy",
        "name_de": "Durchschnittliche Bettenauslastung",
        "name_en": "Bed occupancy rate",
        "definition_en": "Share of available bed-days that were occupied, in percent "
        "(leap years use 366 days).",
        "unit": "percent",
        "is_derived": True,
        "formula": "bed_days / (beds * days_in_year) * 100",
    },
]

# Published Destatis derived values kept only for validation (recomputed vs published).
PUBLISHED_CHECK_INDICATORS = [
    "beds_per_100k_published",
    "cases_per_100k_published",
    "alos_published",
    "occupancy_published",
]


def indicator_ids() -> list[str]:
    return [i["indicator_id"] for i in INDICATORS]
