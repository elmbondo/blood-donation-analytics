-- ============================================================
-- KENYA BLOOD DONATION ANALYTICS — SQL QUERIES
-- ============================================================


-- ── Q1: Which counties have the lowest donor-to-population ratio? ─────────
-- Why this matters: identifies where donation campaigns should be targeted.
-- Manual logic: count donors per county, divide by population, rank ascending.

CREATE OR REPLACE VIEW vw_donor_density AS
SELECT
    dc.county_name,
    dc.region,
    dc.population,
    COUNT(dd.donor_key)                                      AS total_donors,
    ROUND(COUNT(dd.donor_key) * 10000.0 / dc.population, 2) AS donors_per_10k
FROM dim_counties dc
LEFT JOIN dim_donors dd ON dc.county_name = dd.county_name
GROUP BY dc.county_name, dc.region, dc.population
ORDER BY donors_per_10k ASC;

SELECT * FROM vw_donor_density LIMIT 15;


-- ── Q2: Which blood types are most frequently in shortage? ────────────────
-- Shortage = fulfilled < requested. Group by blood type.

CREATE OR REPLACE VIEW vw_blood_type_shortage AS
SELECT
    dbt.blood_type,
    dbt.rarity_category,
    COUNT(*)                                            AS total_requests,
    SUM(fbr.units_requested)                            AS units_requested,
    SUM(fbr.units_fulfilled)                            AS units_fulfilled,
    SUM(fbr.units_requested - fbr.units_fulfilled)      AS units_shortfall,
    ROUND(AVG(fbr.fulfillment_rate) * 100, 1)          AS avg_fulfillment_pct
FROM fact_blood_requests fbr
JOIN dim_blood_types dbt ON fbr.blood_type_key = dbt.blood_type_key
GROUP BY dbt.blood_type, dbt.rarity_category
ORDER BY avg_fulfillment_pct ASC;

SELECT * FROM vw_blood_type_shortage;


-- ── Q3: Monthly donation trend over 3 years ───────────────────────────────
-- Useful for spotting seasonality and growth over time.

CREATE OR REPLACE VIEW vw_monthly_donations AS
SELECT
    dt.year,
    dt.month_num,
    dt.month_name,
    COUNT(fd.donation_id)   AS total_donations,
    SUM(fd.units_donated)   AS total_units
FROM fact_donations fd
JOIN dim_time dt ON fd.time_key = dt.time_key
WHERE fd.status = 'Completed'
GROUP BY dt.year, dt.month_num, dt.month_name
ORDER BY dt.year, dt.month_num;

SELECT * FROM vw_monthly_donations;


-- ── Q4: Which hospitals have the highest unfulfilled request rates? ────────

CREATE OR REPLACE VIEW vw_hospital_performance AS
SELECT
    dh.hospital_name,
    dh.county_name,
    dh.facility_level,
    COUNT(fbr.request_id)                          AS total_requests,
    ROUND(AVG(fbr.fulfillment_rate) * 100, 1)     AS avg_fulfillment_pct,
    SUM(fbr.units_requested - fbr.units_fulfilled) AS total_shortfall
FROM fact_blood_requests fbr
JOIN dim_hospitals dh ON fbr.hospital_key = dh.hospital_key
GROUP BY dh.hospital_name, dh.county_name, dh.facility_level
ORDER BY avg_fulfillment_pct ASC
LIMIT 20;

SELECT * FROM vw_hospital_performance;


-- ── Q5: Repeat donors vs one-time donors ─────────────────────────────────
-- Retention insight: what % of donors donate more than once?

CREATE OR REPLACE VIEW vw_donor_retention AS
SELECT
    donation_counts.donation_count_bucket,
    COUNT(*)                                        AS num_donors,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct_of_donors
FROM (
    SELECT
        donor_key,
        CASE
            WHEN COUNT(*) = 1 THEN 'One-time'
            WHEN COUNT(*) BETWEEN 2 AND 3 THEN '2-3 times'
            WHEN COUNT(*) BETWEEN 4 AND 6 THEN '4-6 times'
            ELSE '7+ times'
        END AS donation_count_bucket
    FROM fact_donations
    WHERE status = 'Completed'
    GROUP BY donor_key
) donation_counts
GROUP BY donation_counts.donation_count_bucket
ORDER BY num_donors DESC;

SELECT * FROM vw_donor_retention;


-- ── Q6: Which months see the highest demand spikes? ───────────────────────

CREATE OR REPLACE VIEW vw_monthly_demand AS
SELECT
    dt.month_name,
    dt.month_num,
    SUM(fbr.units_requested)                        AS total_units_requested,
    SUM(fbr.units_fulfilled)                        AS total_units_fulfilled,
    SUM(fbr.units_requested - fbr.units_fulfilled)  AS total_shortfall,
    ROUND(AVG(fbr.fulfillment_rate) * 100, 1)      AS avg_fulfillment_pct
FROM fact_blood_requests fbr
JOIN dim_time dt ON fbr.time_key = dt.time_key
GROUP BY dt.month_name, dt.month_num
ORDER BY total_units_requested DESC;

SELECT * FROM vw_monthly_demand;


-- ── Q7: Fulfillment by urgency level ─────────────────────────────────────
-- Do emergency requests get prioritised? This should show higher fulfillment
-- for Emergency than Routine.

CREATE OR REPLACE VIEW vw_urgency_fulfillment AS
SELECT
    urgency_level,
    COUNT(*)                                    AS total_requests,
    ROUND(AVG(fulfillment_rate) * 100, 1)      AS avg_fulfillment_pct,
    SUM(units_requested)                        AS total_requested,
    SUM(units_fulfilled)                        AS total_fulfilled
FROM fact_blood_requests
GROUP BY urgency_level
ORDER BY avg_fulfillment_pct DESC;

SELECT * FROM vw_urgency_fulfillment;


-- ── Q8: Donations on vs off public holidays ───────────────────────────────
-- Confirms whether the holiday spike we built in is visible in the data.

CREATE OR REPLACE VIEW vw_holiday_donations AS
SELECT
    dt.is_public_holiday,
    COUNT(fd.donation_id)                           AS total_donations,
    ROUND(COUNT(fd.donation_id) * 1.0 /
          COUNT(DISTINCT dt.full_date), 1)          AS avg_donations_per_day
FROM fact_donations fd
JOIN dim_time dt ON fd.time_key = dt.time_key
WHERE fd.status = 'Completed'
GROUP BY dt.is_public_holiday;

SELECT * FROM vw_holiday_donations;


-- ── Q9: Supply vs demand gap by region ───────────────────────────────────

CREATE OR REPLACE VIEW vw_regional_gap AS
SELECT
    dh.region,
    SUM(fbr.units_requested)                        AS total_requested,
    SUM(fbr.units_fulfilled)                        AS total_fulfilled,
    SUM(fbr.units_requested - fbr.units_fulfilled)  AS gap,
    ROUND(AVG(fbr.fulfillment_rate) * 100, 1)      AS avg_fulfillment_pct
FROM fact_blood_requests fbr
JOIN dim_hospitals dh ON fbr.hospital_key = dh.hospital_key
GROUP BY dh.region
ORDER BY gap DESC;

SELECT * FROM vw_regional_gap;


-- ── Q10: Facility level supply constraint ─────────────────────────────────

CREATE OR REPLACE VIEW vw_facility_level_supply AS
SELECT
    dh.facility_level,
    COUNT(DISTINCT dh.hospital_key)                 AS num_hospitals,
    SUM(fbr.units_requested)                        AS total_requested,
    SUM(fbr.units_fulfilled)                        AS total_fulfilled,
    ROUND(AVG(fbr.fulfillment_rate) * 100, 1)      AS avg_fulfillment_pct
FROM fact_blood_requests fbr
JOIN dim_hospitals dh ON fbr.hospital_key = dh.hospital_key
GROUP BY dh.facility_level
ORDER BY avg_fulfillment_pct ASC;

SELECT * FROM vw_facility_level_supply;