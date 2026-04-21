-- E-COMMERCE ANALYTICS PIPELINE - ANALYTICAL VIEWS
-- Created: 2024-04-21
--
-- COST NOTE: views do not store data. Query costs depend on underlying tables.
-- All views filter on partition columns to minimize bytes scanned.

-- ============================================================================
-- VIEW 1: v_revenue_by_region
-- Business objective: Analyze regional revenue performance with MoM growth
-- ============================================================================

CREATE OR REPLACE VIEW `{project_id}.{dataset}.v_revenue_by_region` AS
WITH regional_revenue AS (
  SELECT
    region,
    DATE_TRUNC(DATE(order_date), MONTH) as month,
    SUM(total_amount) as monthly_revenue,
    COUNT(DISTINCT order_id) as monthly_orders,
    AVG(total_amount) as avg_basket_size,
    COUNT(DISTINCT client_id) as monthly_clients
  FROM `{project_id}.{dataset}.orders`
  WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 13 MONTH)
    AND status = 'Delivered'
  GROUP BY region, month
)
SELECT
  region,
  month,
  monthly_revenue,
  monthly_orders,
  ROUND(avg_basket_size, 2) as avg_basket_size,
  monthly_clients,
  ROUND(
    100 * monthly_revenue / SUM(monthly_revenue) OVER (PARTITION BY month),
    2
  ) as pct_of_global_revenue,
  ROUND(
    100 * (monthly_revenue - LAG(monthly_revenue) OVER (PARTITION BY region ORDER BY month)) 
    / LAG(monthly_revenue) OVER (PARTITION BY region ORDER BY month),
    2
  ) as mom_growth_pct
FROM regional_revenue
ORDER BY month DESC, monthly_revenue DESC;


-- ============================================================================
-- VIEW 2: v_inactive_clients
-- Business objective: Identify at-risk clients with no recent purchases
-- ============================================================================

CREATE OR REPLACE VIEW `{project_id}.{dataset}.v_inactive_clients` AS
WITH client_order_history AS (
  SELECT
    c.client_id,
    c.last_name,
    c.first_name,
    c.email,
    c.country,
    c.segment,
    MAX(o.order_date) as last_purchase_date,
    COUNT(DISTINCT o.order_id) as total_orders,
    SUM(o.total_amount) as historical_revenue,
    COUNT(DISTINCT i.incident_id) as incident_count
  FROM `{project_id}.{dataset}.clients` c
  LEFT JOIN `{project_id}.{dataset}.orders` o
    ON c.client_id = o.client_id
    AND o.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR)
  LEFT JOIN `{project_id}.{dataset}.incidents` i
    ON c.client_id = i.client_id
    AND i.report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR)
  WHERE c.registration_date < DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
  GROUP BY c.client_id, c.last_name, c.first_name, c.email, c.country, c.segment
)
SELECT
  client_id,
  last_name,
  first_name,
  email,
  country,
  segment,
  last_purchase_date,
  total_orders,
  ROUND(COALESCE(historical_revenue, 0), 2) as historical_revenue,
  incident_count,
  DATE_DIFF(CURRENT_DATE(), CAST(last_purchase_date AS DATE), DAY) as days_inactive
FROM client_order_history
WHERE last_purchase_date < DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
  OR last_purchase_date IS NULL
ORDER BY historical_revenue DESC;


-- ============================================================================
-- VIEW 3: v_top_products
-- Business objective: Product performance ranking by category
-- ============================================================================

CREATE OR REPLACE VIEW `{project_id}.{dataset}.v_top_products` AS
WITH product_stats AS (
  SELECT
    p.product_id,
    p.product_name,
    p.category,
    SUM(oi.quantity * oi.unit_price) as revenue,
    SUM(oi.quantity) as units_sold,
    COUNT(DISTINCT oi.order_id) as distinct_orders,
    ROUND(
      100 * COUNTIF(o.status = 'Cancelled') / COUNT(DISTINCT o.order_id),
      2
    ) as cancellation_rate
  FROM `{project_id}.{dataset}.products` p
  LEFT JOIN `{project_id}.{dataset}.order_items` oi
    ON p.product_id = oi.product_id
    AND oi.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
  LEFT JOIN `{project_id}.{dataset}.orders` o
    ON oi.order_id = o.order_id
  GROUP BY p.product_id, p.product_name, p.category
)
SELECT
  product_id,
  product_name,
  category,
  ROUND(COALESCE(revenue, 0), 2) as revenue,
  COALESCE(units_sold, 0) as units_sold,
  COALESCE(distinct_orders, 0) as distinct_orders,
  COALESCE(cancellation_rate, 0) as cancellation_rate,
  RANK() OVER (PARTITION BY category ORDER BY revenue DESC) as rank_in_category
FROM product_stats
WHERE revenue > 0
ORDER BY category, revenue DESC;


-- ============================================================================
-- VIEW 4: v_recurring_incidents
-- Business objective: Support quality metrics by incident category
-- ============================================================================

CREATE OR REPLACE VIEW `{project_id}.{dataset}.v_recurring_incidents` AS
WITH incident_stats AS (
  SELECT
    i.category,
    COUNT(DISTINCT i.incident_id) as incident_count,
    ROUND(AVG(CAST(i.resolution_time_h AS FLOAT64)), 1) as avg_resolution_hours,
    ROUND(
      100 * COUNTIF(i.status = 'Escalated') / COUNT(*),
      2
    ) as escalation_rate,
    ROUND(
      100 * COUNTIF(i.priority = 'Critical') / COUNT(*),
      2
    ) as critical_rate,
    COUNTIF(i.order_id IS NOT NULL) as linked_to_order,
    ROUND(
      100 * COUNTIF(i.order_id IS NOT NULL) / COUNT(*),
      2
    ) as pct_linked_to_order
  FROM `{project_id}.{dataset}.incidents` i
  WHERE i.report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
  GROUP BY i.category
)
SELECT
  category,
  incident_count,
  avg_resolution_hours,
  escalation_rate,
  critical_rate,
  linked_to_order,
  pct_linked_to_order
FROM incident_stats
ORDER BY incident_count DESC;


-- ============================================================================
-- VIEW 5: v_navigation_funnel
-- Business objective: User engagement and device preferences by page
-- ============================================================================

CREATE OR REPLACE VIEW `{project_id}.{dataset}.v_navigation_funnel` AS
WITH page_metrics AS (
  SELECT
    page,
    COUNT(DISTINCT session_id) as session_count,
    ROUND(AVG(CAST(duration_seconds AS FLOAT64)), 1) as avg_duration_seconds,
    COUNT(DISTINCT client_id) as unique_users,
    ROUND(
      100 * COUNTIF(device = 'Mobile') / COUNT(*),
      2
    ) as pct_mobile,
    ROUND(
      100 * COUNTIF(device = 'Desktop') / COUNT(*),
      2
    ) as pct_desktop,
    ROUND(
      100 * COUNTIF(device = 'Tablet') / COUNT(*),
      2
    ) as pct_tablet
  FROM `{project_id}.{dataset}.page_views`
  WHERE event_datetime >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
  GROUP BY page
)
SELECT
  page,
  session_count,
  avg_duration_seconds,
  unique_users,
  pct_mobile,
  pct_desktop,
  pct_tablet,
  ROUND(
    (avg_duration_seconds * session_count / 1000),
    2
  ) as engagement_score
FROM page_metrics
ORDER BY session_count DESC;


-- ============================================================================
-- VIEW 6: v_weekly_kpis
-- Business objective: Weekly key performance indicators with WoW trends
-- ============================================================================

CREATE OR REPLACE VIEW `{project_id}.{dataset}.v_weekly_kpis` AS
WITH weekly_stats AS (
  SELECT
    ISO_WEEK(DATE(o.order_date)) as iso_week,
    ISO_YEAR(DATE(o.order_date)) as iso_year,
    SUM(o.total_amount) as weekly_revenue,
    COUNT(DISTINCT o.order_id) as weekly_orders,
    COUNT(DISTINCT CASE 
      WHEN DATE(c.registration_date) >= DATE_TRUNC(DATE(o.order_date), WEEK) 
      THEN c.client_id 
    END) as new_clients,
    COUNT(DISTINCT i.incident_id) as incident_count
  FROM `{project_id}.{dataset}.orders` o
  LEFT JOIN `{project_id}.{dataset}.clients` c
    ON o.client_id = c.client_id
  LEFT JOIN `{project_id}.{dataset}.incidents` i
    ON o.client_id = i.client_id
    AND i.report_date >= DATE_TRUNC(DATE(o.order_date), WEEK)
  WHERE o.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
    AND o.status = 'Delivered'
  GROUP BY iso_year, iso_week
)
SELECT
  iso_year,
  iso_week,
  weekly_revenue,
  weekly_orders,
  new_clients,
  incident_count,
  ROUND(
    LAG(weekly_revenue) OVER (ORDER BY iso_year, iso_week),
    2
  ) as prev_week_revenue,
  ROUND(
    100 * (weekly_revenue - LAG(weekly_revenue) OVER (ORDER BY iso_year, iso_week))
    / LAG(weekly_revenue) OVER (ORDER BY iso_year, iso_week),
    2
  ) as wow_growth_pct
FROM weekly_stats
ORDER BY iso_year DESC, iso_week DESC;


-- ============================================================================
-- VIEW 7: v_client_360
-- Business objective: Comprehensive customer profile with value segmentation
-- ============================================================================

CREATE OR REPLACE VIEW `{project_id}.{dataset}.v_client_360` AS
WITH client_profile AS (
  SELECT
    c.client_id,
    c.last_name,
    c.first_name,
    c.email,
    c.country,
    c.segment,
    c.registration_date,
    ROUND(COALESCE(SUM(o.total_amount), 0), 2) as lifetime_revenue,
    COUNT(DISTINCT o.order_id) as order_count,
    ROUND(
      COALESCE(AVG(o.total_amount), 0),
      2
    ) as avg_basket_size,
    COUNT(DISTINCT i.incident_id) as incident_count,
    MAX(CASE 
      WHEN DENSE_RANK() OVER (PARTITION BY c.client_id ORDER BY COUNT(*) DESC) = 1 
      THEN i.category 
    END) as top_incident_category,
    COUNT(DISTINCT pv.page) as pages_visited,
    MAX(CASE 
      WHEN DENSE_RANK() OVER (PARTITION BY c.client_id ORDER BY COUNT(*) DESC) = 1 
      THEN pv.page 
    END) as favorite_page,
    MAX(CASE 
      WHEN DENSE_RANK() OVER (PARTITION BY c.client_id ORDER BY COUNT(*) DESC) = 1 
      THEN pv.device 
    END) as primary_device
  FROM `{project_id}.{dataset}.clients` c
  LEFT JOIN `{project_id}.{dataset}.orders` o
    ON c.client_id = o.client_id
  LEFT JOIN `{project_id}.{dataset}.incidents` i
    ON c.client_id = i.client_id
  LEFT JOIN `{project_id}.{dataset}.page_views` pv
    ON c.client_id = pv.client_id
  GROUP BY c.client_id, c.last_name, c.first_name, c.email, c.country, c.segment, c.registration_date
)
SELECT
  client_id,
  last_name,
  first_name,
  email,
  country,
  segment,
  registration_date,
  lifetime_revenue,
  order_count,
  avg_basket_size,
  incident_count,
  top_incident_category,
  pages_visited,
  favorite_page,
  primary_device,
  ROUND(
    lifetime_revenue * 0.5 
    + (20.0 / NULLIF(CAST(incident_count AS FLOAT64), 0))
    + order_count * 2,
    2
  ) as value_score,
  CASE 
    WHEN (lifetime_revenue * 0.5 + (20.0 / NULLIF(CAST(incident_count AS FLOAT64), 0)) + order_count * 2) > 200 THEN 'VIP'
    WHEN (lifetime_revenue * 0.5 + (20.0 / NULLIF(CAST(incident_count AS FLOAT64), 0)) + order_count * 2) BETWEEN 50 AND 200 THEN 'Regular'
    ELSE 'At risk'
  END as value_segment
FROM client_profile
ORDER BY lifetime_revenue DESC;
