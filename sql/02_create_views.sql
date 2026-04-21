-- ============================================================================
-- BIGQUERY ANALYTICAL VIEWS - BASED ON ACTUAL DATA STRUCTURE
-- ============================================================================

-- ============================================================================
-- 1. REVENUE BY REGION
-- ============================================================================

CREATE OR REPLACE VIEW ecommerce_analytics.v_revenue_by_region AS
SELECT
  o.region,
  TIMESTAMP_TRUNC(o.order_date, MONTH) AS month,
  COUNT(DISTINCT o.order_id) AS order_count,
  COUNT(DISTINCT o.client_id) AS unique_customers,
  SUM(o.total_amount) AS total_revenue,
  ROUND(AVG(o.total_amount), 2) AS avg_order_value
FROM ecommerce_analytics.orders o
WHERE o.status = 'Delivered'
GROUP BY o.region, month
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
  COUNT(DISTINCT o.order_id) AS lifetime_orders,
  SUM(o.total_amount) AS lifetime_revenue
FROM ecommerce_analytics.clients c
LEFT JOIN ecommerce_analytics.orders o ON c.client_id = o.client_id
GROUP BY c.client_id, c.first_name, c.last_name, c.email, c.country
ORDER BY lifetime_revenue DESC;

-- ============================================================================
-- 3. TOP PRODUCTS BY REVENUE
-- ============================================================================

CREATE OR REPLACE VIEW ecommerce_analytics.v_top_products AS
SELECT
  p.product_id,
  p.product_name,
  p.category,
  COUNT(DISTINCT oi.order_id) AS order_count,
  SUM(oi.quantity) AS total_quantity_sold,
  SUM(oi.quantity * oi.unit_price) AS total_revenue
FROM ecommerce_analytics.products p
LEFT JOIN ecommerce_analytics.order_items oi ON p.product_id = oi.product_id
GROUP BY p.product_id, p.product_name, p.category
ORDER BY total_revenue DESC
LIMIT 50;

-- ============================================================================
-- 4. INCIDENTS BY CATEGORY
-- ============================================================================

CREATE OR REPLACE VIEW ecommerce_analytics.v_incidents_summary AS
SELECT
  category,
  priority,
  COUNT(*) AS incident_count,
  COUNT(DISTINCT client_id) AS affected_customers,
  ROUND(AVG(CAST(resolution_time_h AS FLOAT64)), 1) AS avg_resolution_hours
FROM ecommerce_analytics.incidents
GROUP BY category, priority
ORDER BY incident_count DESC;

-- ============================================================================
-- 5. PAGE VIEWS SUMMARY
-- ============================================================================

CREATE OR REPLACE VIEW ecommerce_analytics.v_page_views_summary AS
SELECT
  page,
  device,
  traffic_source,
  COUNT(DISTINCT session_id) AS session_count,
  COUNT(DISTINCT client_id) AS unique_visitors,
  ROUND(AVG(duration_seconds), 2) AS avg_duration_seconds
FROM ecommerce_analytics.page_views
WHERE TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), event_datetime, DAY) <= 7
GROUP BY page, device, traffic_source
ORDER BY session_count DESC;

-- ============================================================================
-- 6. CUSTOMER LIFETIME VALUE
-- ============================================================================

CREATE OR REPLACE VIEW ecommerce_analytics.v_customer_ltv AS
SELECT
  c.client_id,
  c.first_name,
  c.last_name,
  c.email,
  c.country,
  c.registration_date,
  COUNT(DISTINCT o.order_id) AS total_orders,
  SUM(o.total_amount) AS total_revenue,
  ROUND(AVG(o.total_amount), 2) AS avg_order_value,
  MAX(o.order_date) AS last_order_date
FROM ecommerce_analytics.clients c
LEFT JOIN ecommerce_analytics.orders o ON c.client_id = o.client_id
GROUP BY c.client_id, c.first_name, c.last_name, c.email, c.country, c.registration_date
ORDER BY total_revenue DESC;
