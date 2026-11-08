-- Stage 4 validation checks (DuckDB). Each query returns the OFFENDING rows; an empty result
-- means the check passed. Run by etl/validate.py, which fails loudly on any non-empty result.

-- check: no duplicate (ags_code, year, indicator_id) in the long fact table
-- name: duplicates
SELECT ags_code, year, indicator_id, count(*) AS n
FROM fact_indicators
GROUP BY ags_code, year, indicator_id
HAVING count(*) > 1;

-- check: exactly 16 Länder (excluding the Germany total) per (year, indicator_id)
-- name: sixteen_laender
SELECT year, indicator_id, count(DISTINCT ags_code) AS n_laender
FROM fact_indicators
WHERE ags_code <> 'DG'
GROUP BY year, indicator_id
HAVING count(DISTINCT ags_code) <> 16;

-- check: no negative values among the non-null measures
-- name: no_negatives
SELECT ags_code, year, indicator_id, value
FROM fact_indicators
WHERE value < 0;

-- check: additive indicators — sum over the 16 Länder equals the Germany total (<= 0.1%)
-- name: additivity
WITH s AS (
    SELECT year, indicator_id, sum(value) AS sum_laender
    FROM fact_indicators WHERE ags_code <> 'DG'
      AND indicator_id IN ('hospitals', 'beds', 'cases', 'bed_days')
    GROUP BY year, indicator_id
),
g AS (
    SELECT year, indicator_id, value AS germany
    FROM fact_indicators WHERE ags_code = 'DG'
      AND indicator_id IN ('hospitals', 'beds', 'cases', 'bed_days')
)
SELECT s.year, s.indicator_id, s.sum_laender, g.germany,
       abs(s.sum_laender - g.germany) / g.germany * 100 AS pct_diff
FROM s JOIN g USING (year, indicator_id)
WHERE abs(s.sum_laender - g.germany) / g.germany * 100 > 0.1;
