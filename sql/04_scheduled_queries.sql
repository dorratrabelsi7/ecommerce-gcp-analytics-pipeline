-- E-COMMERCE ANALYTICS PIPELINE - SCHEDULED QUERIES
-- Created: 2024-04-21
--
-- These queries are designed for BigQuery Scheduled Queries (free tier allows up to 10)
-- Both queries use partition filters to stay within free tier query costs

-- ============================================================================
-- SCHEDULED QUERY 1: DAILY KPI REFRESH
-- Schedule: Every day at 06:00 UTC (via Cloud Scheduler)
-- Estimated cost: 1-5 MB scanned (last 2 days partition only)
--
-- Business objective: Refresh daily aggregated metrics for dashboard
-- ============================================================================

CREATE OR REPLACE TABLE `{project_id}.{dataset}.kpis_daily` AS
SELECT
  CURRENT_DATE() as metric_date,
  COUNT(DISTINCT order_id) as daily_orders,
  ROUND(SUM(total_amount), 2) as daily_revenue,
  COUNT(DISTINCT client_id) as daily_active_clients,
  ROUND(AVG(total_amount), 2) as avg_order_value,
  COUNTIF(status = 'Delivered') as delivered_count,
  COUNTIF(status = 'Pending') as pending_count,
  COUNTIF(status = 'Cancelled') as cancelled_count,
  ROUND(
    100.0 * COUNTIF(status = 'Delivered') / COUNT(*),
    2
  ) as delivery_rate_pct
FROM `{project_id}.{dataset}.orders`
WHERE DATE(order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY)
GROUP BY metric_date;


-- ============================================================================
-- SCHEDULED QUERY 2: WEEKLY RFM SEGMENTATION UPDATE
-- Schedule: Every Monday at 07:00 UTC (via Cloud Scheduler)
-- Estimated cost: 10-20 MB scanned (last 90 days partition only)
--
-- Business objective: Update RFM customer segments for targeted campaigns
-- ============================================================================

CREATE OR REPLACE TABLE `{project_id}.{dataset}.rfm_segments_weekly` AS
WITH rfm_calc AS (
  SELECT
    c.client_id,
    c.email,
    c.segment as current_segment,
    DATE_DIFF(CURRENT_DATE(), MAX(DATE(o.order_date)), DAY) as recency_days,
    COUNT(DISTINCT o.order_id) as frequency,
    ROUND(SUM(o.total_amount), 2) as monetary_value,
    NTILE(4) OVER (ORDER BY DATE_DIFF(CURRENT_DATE(), MAX(DATE(o.order_date)), DAY) DESC) as recency_quartile,
    NTILE(4) OVER (ORDER BY COUNT(DISTINCT o.order_id)) as frequency_quartile,
    NTILE(4) OVER (ORDER BY SUM(o.total_amount)) as monetary_quartile
  FROM `{project_id}.{dataset}.clients` c
  LEFT JOIN `{project_id}.{dataset}.orders` o
    ON c.client_id = o.client_id
    AND o.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
  GROUP BY c.client_id, c.email, c.segment
)
SELECT
  CURRENT_DATE() as segment_date,
  client_id,
  email,
  current_segment,
  recency_days,
  frequency,
  monetary_value,
  CONCAT(
    CAST(recency_quartile AS STRING), '-',
    CAST(frequency_quartile AS STRING), '-',
    CAST(monetary_quartile AS STRING)
  ) as rfm_code,
  CASE
    WHEN recency_quartile = 1 AND frequency_quartile IN (1, 2) AND monetary_quartile IN (1, 2) THEN 'Champions'
    WHEN recency_quartile IN (1, 2) AND frequency_quartile IN (1, 2, 3) THEN 'Loyal'
    WHEN recency_quartile IN (3, 4) AND monetary_quartile >= 2 THEN 'At Risk'
    WHEN recency_quartile = 4 THEN 'Lost'
    ELSE 'Other'
  END as rfm_segment
FROM rfm_calc
ORDER BY monetary_value DESC;
