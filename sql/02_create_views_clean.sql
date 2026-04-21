-- ============================================================================
-- CREATE BIGQUERY ANALYTICAL VIEWS
-- ============================================================================

-- ============================================================================
-- 1. REVENUE BY REGION
-- ============================================================================

CREATE OR REPLACE VIEW ecommerce_analytics.v_revenue_by_region AS
SELECT
  o.country,
  DATE_TRUNC(o.order_date, MONTH) AS month,
  COUNT(DISTINCT o.order_id) AS order_count,
  COUNT(DISTINCT o.client_id) AS unique_customers,
  SUM(o.total_amount) AS total_revenue,
  ROUND(AVG(o.total_amount), 2) AS avg_order_value,
  ROUND(SUM(o.total_amount) / NULLIF(COUNT(DISTINCT o.client_id), 0), 2) AS revenue_per_customer
FROM ecommerce_analytics.orders o
GROUP BY o.country, month
ORDER BY month DESC, total_revenue DESC;

-- ============================================================================
-- 2. INACTIVE CLIENTS
-- ============================================================================

CREATE OR REPLACE VIEW ecommerce_analytics.v_inactive_clients AS
SELECT
  c.client_id,
  c.first_name,
  c.last_name,
  c.email,
  c.country,
  c.registration_date,
  MAX(o.order_date) AS last_order_date,
  DATE_DIFF(CURRENT_DATE(), MAX(o.order_date), DAY) AS days_since_last_order,
  COUNT(o.order_id) AS lifetime_orders,
  SUM(o.total_amount) AS lifetime_revenue
FROM ecommerce_analytics.clients c
LEFT JOIN ecommerce_analytics.orders o ON c.client_id = o.client_id
GROUP BY c.client_id, c.first_name, c.last_name, c.email, c.country, c.registration_date
HAVING DATE_DIFF(CURRENT_DATE(), MAX(o.order_date), DAY) > 90 OR MAX(o.order_date) IS NULL
ORDER BY days_since_last_order DESC;

-- ============================================================================
-- 3. TOP PRODUCTS BY REVENUE
-- ============================================================================

CREATE OR REPLACE VIEW ecommerce_analytics.v_top_products AS
SELECT
  p.product_id,
  p.name,
  p.category,
  p.price,
  COUNT(DISTINCT oi.order_id) AS order_count,
  SUM(oi.quantity) AS total_quantity_sold,
  SUM(oi.line_total) AS total_revenue,
  ROUND(SUM(oi.line_total) / NULLIF(SUM(oi.quantity), 0), 2) AS avg_selling_price,
  ROUND(100 * SUM(oi.line_total) / (SELECT SUM(line_total) FROM ecommerce_analytics.order_items), 2) AS revenue_share_pct
FROM ecommerce_analytics.products p
LEFT JOIN ecommerce_analytics.order_items oi ON p.product_id = oi.product_id
GROUP BY p.product_id, p.name, p.category, p.price
ORDER BY total_revenue DESC
LIMIT 100;

-- ============================================================================
-- 4. RECURRING INCIDENTS
-- ============================================================================

CREATE OR REPLACE VIEW ecommerce_analytics.v_recurring_incidents AS
SELECT
  category,
  priority,
  COUNT(*) AS incident_count,
  ROUND(100 * COUNT(*) / (SELECT COUNT(*) FROM ecommerce_analytics.incidents), 2) AS pct_of_total,
  COUNT(DISTINCT client_id) AS affected_customers,
  ROUND(AVG(CASE WHEN resolved_date IS NOT NULL THEN DATE_DIFF(resolved_date, report_date, DAY) END), 1) AS avg_resolution_days,
  APPROX_QUANTILES(CASE WHEN resolved_date IS NOT NULL THEN DATE_DIFF(resolved_date, report_date, DAY) END, 100)[OFFSET(50)] AS median_resolution_days
FROM ecommerce_analytics.incidents
GROUP BY category, priority
ORDER BY incident_count DESC;

-- ============================================================================
-- 5. NAVIGATION FUNNEL
-- ============================================================================

CREATE OR REPLACE VIEW ecommerce_analytics.v_navigation_funnel AS
SELECT
  page_title,
  COUNT(DISTINCT session_id) AS session_count,
  COUNT(DISTINCT client_id) AS unique_visitors,
  ROUND(100 * COUNT(DISTINCT session_id) / FIRST_VALUE(COUNT(DISTINCT session_id)) OVER (ORDER BY page_title), 2) AS funnel_pct
FROM ecommerce_analytics.page_views
WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY page_title
ORDER BY session_count DESC;

-- ============================================================================
-- 6. WEEKLY KPIs
-- ============================================================================

CREATE OR REPLACE VIEW ecommerce_analytics.v_weekly_kpis AS
SELECT
  EXTRACT(YEAR FROM o.order_date) AS year,
  EXTRACT(WEEK FROM o.order_date) AS week,
  DATE_TRUNC(o.order_date, WEEK) AS week_start,
  COUNT(DISTINCT o.order_id) AS orders,
  COUNT(DISTINCT o.client_id) AS unique_customers,
  SUM(o.total_amount) AS revenue,
  ROUND(SUM(o.total_amount) / NULLIF(COUNT(DISTINCT o.order_id), 0), 2) AS avg_order_value,
  COUNT(DISTINCT i.incident_id) AS support_tickets,
  COUNT(DISTINCT pv.page_view_id) AS page_views
FROM ecommerce_analytics.orders o
LEFT JOIN ecommerce_analytics.incidents i ON DATE_TRUNC(i.report_date, WEEK) = DATE_TRUNC(o.order_date, WEEK)
LEFT JOIN ecommerce_analytics.page_views pv ON DATE_TRUNC(DATE(pv.event_datetime), WEEK) = DATE_TRUNC(o.order_date, WEEK)
GROUP BY year, week, week_start
ORDER BY week_start DESC;

-- ============================================================================
-- 7. CUSTOMER 360 VIEW
-- ============================================================================

CREATE OR REPLACE VIEW ecommerce_analytics.v_customer_360 AS
SELECT
  c.client_id,
  c.first_name,
  c.last_name,
  c.email,
  c.country,
  c.registration_date,
  DATE_DIFF(CURRENT_DATE(), c.registration_date, DAY) AS customer_age_days,
  COUNT(DISTINCT o.order_id) AS lifetime_orders,
  SUM(o.total_amount) AS lifetime_revenue,
  ROUND(AVG(o.total_amount), 2) AS avg_order_value,
  MAX(o.order_date) AS last_order_date,
  DATE_DIFF(CURRENT_DATE(), MAX(o.order_date), DAY) AS days_since_last_purchase,
  COUNT(DISTINCT i.incident_id) AS total_incidents,
  COUNT(DISTINCT CASE WHEN i.status = 'Open' THEN i.incident_id END) AS open_incidents,
  COUNT(DISTINCT pv.session_id) AS website_sessions
FROM ecommerce_analytics.clients c
LEFT JOIN ecommerce_analytics.orders o ON c.client_id = o.client_id
LEFT JOIN ecommerce_analytics.incidents i ON c.client_id = i.client_id
LEFT JOIN ecommerce_analytics.page_views pv ON c.client_id = pv.client_id
GROUP BY c.client_id, c.first_name, c.last_name, c.email, c.country, c.registration_date
ORDER BY lifetime_revenue DESC;
