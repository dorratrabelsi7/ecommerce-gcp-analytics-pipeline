-- E-COMMERCE ANALYTICS PIPELINE - ADVANCED ANALYTICS
-- Created: 2024-04-21
--
-- Advanced queries for deeper insights. Each query includes cost estimation.
-- ESTIMATED BYTES SCANNED refers to partition-filtered queries.

-- ============================================================================
-- QUERY 1: RFM SEGMENTATION
-- Business objective: Classify customers by Recency, Frequency, Monetary value
-- ESTIMATED BYTES SCANNED: ~50 MB (partition filter on last 12 months)
-- ============================================================================

SELECT
  client_id,
  NTILE(4) OVER (ORDER BY MAX(DATE(order_date)) DESC) as recency_quartile,
  NTILE(4) OVER (ORDER BY COUNT(DISTINCT order_id)) as frequency_quartile,
  NTILE(4) OVER (ORDER BY SUM(total_amount)) as monetary_quartile,
  CASE
    WHEN NTILE(4) OVER (ORDER BY MAX(DATE(order_date)) DESC) = 1
      AND NTILE(4) OVER (ORDER BY COUNT(DISTINCT order_id)) IN (1, 2)
      AND NTILE(4) OVER (ORDER BY SUM(total_amount)) IN (1, 2)
    THEN 'Champions'
    WHEN NTILE(4) OVER (ORDER BY MAX(DATE(order_date)) DESC) IN (1, 2)
      AND NTILE(4) OVER (ORDER BY COUNT(DISTINCT order_id)) IN (1, 2, 3)
      AND NTILE(4) OVER (ORDER BY SUM(total_amount)) IN (1, 2, 3)
    THEN 'Loyal'
    WHEN NTILE(4) OVER (ORDER BY MAX(DATE(order_date)) DESC) IN (3, 4)
      AND NTILE(4) OVER (ORDER BY SUM(total_amount)) >= 2
    THEN 'At Risk'
    ELSE 'Lost'
  END as rfm_segment,
  ROUND(SUM(total_amount), 2) as lifetime_value,
  COUNT(DISTINCT order_id) as order_frequency,
  MAX(DATE(order_date)) as last_purchase_date
FROM `{project_id}.{dataset}.orders`
WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
GROUP BY client_id
ORDER BY lifetime_value DESC;


-- ============================================================================
-- QUERY 2: MONTHLY COHORT ANALYSIS
-- Business objective: Track customer retention and revenue by registration cohort
-- ESTIMATED BYTES SCANNED: ~30 MB (partition filter + cohort grouping)
-- ============================================================================

WITH cohorts AS (
  SELECT
    DATE_TRUNC(DATE(c.registration_date), MONTH) as cohort_month,
    DATE_TRUNC(DATE(o.order_date), MONTH) as order_month,
    DATE_DIFF(
      DATE_TRUNC(DATE(o.order_date), MONTH),
      DATE_TRUNC(DATE(c.registration_date), MONTH),
      MONTH
    ) as months_since_registration,
    COUNT(DISTINCT c.client_id) as customers,
    ROUND(SUM(o.total_amount), 2) as revenue
  FROM `{project_id}.{dataset}.clients` c
  LEFT JOIN `{project_id}.{dataset}.orders` o
    ON c.client_id = o.client_id
    AND o.order_date >= c.registration_date
  WHERE c.registration_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
  GROUP BY cohort_month, order_month, months_since_registration
)
SELECT
  cohort_month,
  months_since_registration,
  customers,
  revenue,
  LAG(revenue) OVER (PARTITION BY cohort_month ORDER BY months_since_registration) as prev_month_revenue,
  ROUND(
    100 * (revenue - LAG(revenue) OVER (PARTITION BY cohort_month ORDER BY months_since_registration))
    / LAG(revenue) OVER (PARTITION BY cohort_month ORDER BY months_since_registration),
    2
  ) as revenue_growth_pct
FROM cohorts
WHERE months_since_registration >= 0
ORDER BY cohort_month, months_since_registration;


-- ============================================================================
-- QUERY 3: 4-WEEK ROLLING REVENUE TREND
-- Business objective: Identify long-term revenue trends smoothed over 4 weeks
-- ESTIMATED BYTES SCANNED: ~40 MB (partition filter on 6 months)
-- ============================================================================

WITH weekly_revenue AS (
  SELECT
    ISO_WEEK(DATE(order_date)) as week_num,
    ISO_YEAR(DATE(order_date)) as year_num,
    ROUND(SUM(total_amount), 2) as weekly_revenue
  FROM `{project_id}.{dataset}.orders`
  WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
    AND status = 'Delivered'
  GROUP BY year_num, week_num
)
SELECT
  year_num,
  week_num,
  weekly_revenue,
  ROUND(
    AVG(weekly_revenue) OVER (
      ORDER BY year_num, week_num
      ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
    ),
    2
  ) as rolling_4week_avg,
  ROUND(
    weekly_revenue - AVG(weekly_revenue) OVER (
      ORDER BY year_num, week_num
      ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
    ),
    2
  ) as variance_from_rolling_avg
FROM weekly_revenue
ORDER BY year_num DESC, week_num DESC;


-- ============================================================================
-- QUERY 4: REGIONAL ANOMALY DETECTION
-- Business objective: Identify unusually large orders (outliers) per region
-- ESTIMATED BYTES SCANNED: ~50 MB (partition filter + region clustering)
-- ============================================================================

WITH regional_stats AS (
  SELECT
    region,
    AVG(total_amount) as avg_amount,
    STDDEV_POP(total_amount) as stddev_amount
  FROM `{project_id}.{dataset}.orders`
  WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
  GROUP BY region
)
SELECT
  o.order_id,
  o.client_id,
  o.region,
  o.order_date,
  o.total_amount,
  rs.avg_amount,
  rs.stddev_amount,
  ROUND(
    (o.total_amount - rs.avg_amount) / NULLIF(rs.stddev_amount, 0),
    2
  ) as z_score,
  CASE
    WHEN (o.total_amount - rs.avg_amount) / NULLIF(rs.stddev_amount, 0) > 2 THEN 'High anomaly'
    WHEN (o.total_amount - rs.avg_amount) / NULLIF(rs.stddev_amount, 0) < -2 THEN 'Low anomaly'
    ELSE 'Normal'
  END as anomaly_type
FROM `{project_id}.{dataset}.orders` o
JOIN regional_stats rs ON o.region = rs.region
WHERE o.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
  AND ABS((o.total_amount - rs.avg_amount) / NULLIF(rs.stddev_amount, 0)) > 2
ORDER BY ABS((o.total_amount - rs.avg_amount) / NULLIF(rs.stddev_amount, 0)) DESC;


-- ============================================================================
-- QUERY 5: NAVIGATION CONVERSION FUNNEL
-- Business objective: Measure conversion from /products → /cart → /checkout
-- ESTIMATED BYTES SCANNED: ~80 MB (7-day session reconstruction)
-- ============================================================================

WITH funnel_sessions AS (
  SELECT
    session_id,
    client_id,
    MAX(CASE WHEN page = '/products' THEN 1 ELSE 0 END) as visited_products,
    MAX(CASE WHEN page = '/cart' THEN 1 ELSE 0 END) as visited_cart,
    MAX(CASE WHEN page = '/checkout' THEN 1 ELSE 0 END) as visited_checkout,
    MAX(CASE WHEN page = '/checkout' AND event_datetime >= DATE_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
      THEN 1 ELSE 0 END) as completed_checkout
  FROM `{project_id}.{dataset}.page_views`
  WHERE event_datetime >= DATE_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  GROUP BY session_id, client_id
)
SELECT
  'Step 1: Products' as funnel_stage,
  COUNT(DISTINCT session_id) as sessions,
  COUNT(DISTINCT client_id) as unique_clients
FROM funnel_sessions
WHERE visited_products = 1
UNION ALL
SELECT
  'Step 2: Cart (from Products)',
  COUNT(DISTINCT session_id),
  COUNT(DISTINCT client_id)
FROM funnel_sessions
WHERE visited_products = 1 AND visited_cart = 1
UNION ALL
SELECT
  'Step 3: Checkout (from Cart)',
  COUNT(DISTINCT session_id),
  COUNT(DISTINCT client_id)
FROM funnel_sessions
WHERE visited_cart = 1 AND visited_checkout = 1
UNION ALL
SELECT
  'Step 4: Completed',
  COUNT(DISTINCT session_id),
  COUNT(DISTINCT client_id)
FROM funnel_sessions
WHERE completed_checkout = 1;
