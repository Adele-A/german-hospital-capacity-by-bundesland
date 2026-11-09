# Analytical memo — Hospital capacity and utilisation across the German Bundesländer

*Independent portfolio project. Source: Statistisches Bundesamt (Destatis), statistic 23111
"Grunddaten der Krankenhäuser" (dl-de/by-2-0). By-Land years 2022–2024. Every figure traces to
`dashboard/data/fact_indicators_wide.csv`; derivations are documented in
`reports/validation_report.md`.*

This is a descriptive comparison, not an evaluation. **No region's system is "better" or "worse":**
differences reflect age structure, cross-state patient flows, hospital mix and specialisation, and
the Zensus-2022 population revision. **"Fälle" (cases) are treatment cases, not unique patients,**
and are counted at the **hospital's location**, not the patient's place of residence.

## 1. Regional differences in capacity (2024)

Hospital bed provision per 100,000 inhabitants varies about **1.5-fold** across the 16 states —
from **468 (Baden-Württemberg)** and **500 (Lower Saxony)** at the low end to **698 (Hamburg)** and
**697 (Thüringen)** at the high end (national average **566**). The eastern states and the
city-state Hamburg sit above the average; the large south-western states sit below it. Higher
provision is not "more generous care": the city-states concentrate specialised hospitals that also
treat patients from surrounding states, and the eastern states have older populations and lower
population density.

Inpatient **cases per 100,000** follow a similar gradient — highest in **Thüringen (25,155)**,
**Saarland (24,893)** and **Bremen (24,869)**, lowest in **Baden-Württemberg (17,078)**. Part of
this reflects age structure (more hospital stays in older populations) and part reflects where care
is physically delivered rather than where patients live.

## 2. Utilisation is more even than capacity

Utilisation measures cluster much more tightly than provision. In 2024 the **average length of
stay** ranged only from **6.6 to 7.8 days** across states (national **7.1**), and **bed occupancy**
from **68.6% to 77.8%** (national **72.0%**). Capacity differs far more between states than the
intensity with which beds are used — consistent with length of stay being driven mainly by
case-mix and clinical practice rather than by regional bed supply.

## 3. Trends 2022–2024, and the pandemic in national context

At the national level the number of hospitals fell from **1,893 (2022) to 1,841 (2024)** (−2.7%)
and available beds from **480,382 to 472,851** (−1.6%), while **inpatient cases rose from 16.80 to
17.55 million** as activity recovered from the COVID-19 trough. The combination — fewer beds, more
cases — lifted **bed occupancy from 69.0% to 72.0%** and nudged beds per 100k down from 582 to 566.

The by-Land figures start in 2022, so the pandemic itself is read from the **Germany national
series 2000–2024** (`dashboard/data/fact_germany_series.csv`, figure
`reports/figures/national_trend.png`). Inpatient cases peaked at **19.42 million in 2019**, fell
**13.8% to the 2021 trough (16.74 million)**, and had **only partly recovered by 2024 (17.55
million — still 9.6% below the 2019 baseline)**. Meanwhile available beds declined steadily
throughout (≈560k in 2000 → 473k in 2024), independent of the pandemic. So the 2022→2024 rise is
recovery toward, not past, pre-COVID activity. Note too the **population denominator changed basis
after Zensus 2022**, which affects per-100k comparisons across that boundary.

## 4. Berlin–Brandenburg: why the pair must be read together

Berlin and Brandenburg illustrate the location-vs-residence caveat directly. In 2024 Berlin had
**547.6 beds per 100k** with **77.8% occupancy** (the highest of any state), while Brandenburg had
**more beds per 100k (583.5)** but **lower occupancy (70.3%)** and a longer stay (7.69 vs 7.22
days). Berlin's **86 hospitals** draw inpatients from the surrounding Brandenburg commuter belt;
because cases are counted where the hospital is, Berlin's caseload is inflated and Brandenburg's
deflated relative to residence-based figures. Treating the two as **one region** smooths the
cross-border flow: combined, Berlin + Brandenburg show **562 beds per 100k** and **20,750 cases per
100k** — between the two state values and closer to the national pattern. The higher Berlin
occupancy is what one expects for a metropolitan hub, not evidence of a "tighter" system.

## 5. Caveats and open questions

- **Age standardisation.** Differences partly track age structure; age-standardised rates would
  separate demography from provision. (65+ share by state, from statistic 12411, is the next input.)
- **Residence vs location.** A residence-based view (Diagnosedaten, statistic 23131, "Wohnort")
  would correct the city-state inflation — not available tokenless here.
- **Pre-pandemic baseline.** By-Land data here start in 2022; adding 2019 by Land (via the GENESIS
  API with a token, or the archived Fachserie) would anchor the pandemic effect per state.
- **Ambulatory shift & staffing.** Falling bed counts coincide with more day-case/ambulatory care
  and staffing constraints; cases alone do not capture this. Beds by ownership type and staff in
  full-time equivalents (both in statistic 23111) are natural extensions.

*Disclaimer: not affiliated with Destatis or any health authority. Figures are official Destatis
values or documented recomputations from them.*
