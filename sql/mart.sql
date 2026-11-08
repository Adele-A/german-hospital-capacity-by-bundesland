-- Stage 3 mart build (DuckDB). Input: stg_hospital_long (ags_code, year, indicator_id, value,
-- unit, flag, source_id). Output: mart_wide, fact_indicators (long), fact_indicators_wide.
--
-- Derived measures are recomputed from the source columns. population_avg is recovered from the
-- Destatis-published per-100k rate (the Durchschnittsbevölkerung Destatis used); a second estimate
-- from cases is kept for the validation cross-check. Per-100k are then recomputed from it, so they
-- reproduce the published values. ALOS and occupancy are genuine independent recomputations.

CREATE OR REPLACE TABLE _src_wide AS
SELECT
    ags_code,
    year,
    MAX(value) FILTER (WHERE indicator_id = 'hospitals')                 AS hospitals,
    MAX(value) FILTER (WHERE indicator_id = 'beds')                      AS beds,
    MAX(value) FILTER (WHERE indicator_id = 'cases')                     AS cases,
    MAX(value) FILTER (WHERE indicator_id = 'bed_days')                  AS bed_days,
    MAX(value) FILTER (WHERE indicator_id = 'beds_per_100k_published')   AS beds_per_100k_published,
    MAX(value) FILTER (WHERE indicator_id = 'cases_per_100k_published')  AS cases_per_100k_published,
    MAX(value) FILTER (WHERE indicator_id = 'alos_published')            AS alos_published,
    MAX(value) FILTER (WHERE indicator_id = 'occupancy_published')       AS occupancy_published
FROM stg_hospital_long
GROUP BY ags_code, year;

CREATE OR REPLACE TABLE mart_wide AS
WITH d AS (
    SELECT
        *,
        CASE WHEN (year % 4 = 0 AND (year % 100 <> 0 OR year % 400 = 0)) THEN 366 ELSE 365 END
            AS days_in_year,
        CASE WHEN beds_per_100k_published > 0 THEN beds  / beds_per_100k_published  * 100000 END
            AS population_avg,
        CASE WHEN cases_per_100k_published > 0 THEN cases / cases_per_100k_published * 100000 END
            AS population_avg_from_cases
    FROM _src_wide
)
SELECT
    ags_code,
    year,
    hospitals,
    beds,
    cases,
    bed_days,
    population_avg,
    population_avg_from_cases,
    CASE WHEN population_avg > 0 THEN beds  / population_avg * 100000 END AS beds_per_100k,
    CASE WHEN population_avg > 0 THEN cases / population_avg * 100000 END AS cases_per_100k,
    CASE WHEN cases > 0         THEN bed_days / cases END                 AS alos,
    CASE WHEN beds  > 0         THEN bed_days / (beds * days_in_year) * 100 END AS occupancy,
    beds_per_100k_published,
    cases_per_100k_published,
    alos_published,
    occupancy_published,
    days_in_year
FROM d;

-- Long fact table: source indicators keep their provenance; derived indicators are tagged.
CREATE OR REPLACE TABLE fact_indicators AS
SELECT ags_code, year, indicator_id, value, unit, source_id
FROM stg_hospital_long
WHERE indicator_id IN ('hospitals', 'beds', 'cases', 'bed_days')
UNION ALL SELECT ags_code, year, 'population_avg', population_avg, 'persons',
    'derived:implied_from_published_per_100k' FROM mart_wide WHERE population_avg IS NOT NULL
UNION ALL SELECT ags_code, year, 'beds_per_100k', beds_per_100k, 'per_100k', 'derived'
    FROM mart_wide WHERE beds_per_100k IS NOT NULL
UNION ALL SELECT ags_code, year, 'cases_per_100k', cases_per_100k, 'per_100k', 'derived'
    FROM mart_wide WHERE cases_per_100k IS NOT NULL
UNION ALL SELECT ags_code, year, 'alos', alos, 'days', 'derived'
    FROM mart_wide WHERE alos IS NOT NULL
UNION ALL SELECT ags_code, year, 'occupancy', occupancy, 'percent', 'derived'
    FROM mart_wide WHERE occupancy IS NOT NULL;

-- Wide mart for Power BI / quick inspection (the canonical nine indicators).
CREATE OR REPLACE TABLE fact_indicators_wide AS
SELECT ags_code, year, hospitals, beds, cases, bed_days,
       population_avg, beds_per_100k, cases_per_100k, alos, occupancy
FROM mart_wide;
