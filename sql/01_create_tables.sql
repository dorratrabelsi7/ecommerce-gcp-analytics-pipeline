-- E-COMMERCE ANALYTICS PIPELINE - BIGQUERY TABLE SCHEMAS
-- Created: 2024-04-21
-- 
-- COST NOTE: tables are partitioned to minimize query bytes scanned.
-- Always use WHERE clauses on partition columns in production queries.
-- 
-- Partitioning strategy:
-- - clients: partitioned by registration_date (arrival cohorts)
-- - products: no partition (small < 1MB)
-- - orders: partitioned by order_date (time-based queries)
-- - order_items: partitioned by order_date (matches orders)
-- - incidents: partitioned by report_date (time-series analysis)
-- - page_views: partitioned by event_datetime (realtime-like data)
--
-- Clustering improves filter performance within partitions

-- ============================================================================
-- 1. CLIENTS TABLE
-- ============================================================================

CREATE OR REPLACE TABLE `{project_id}.{dataset}.clients` 
PARTITION BY DATE(registration_date)
CLUSTER BY country, segment
AS
SELECT
  client_id,
  last_name,
  first_name,
  email,
  age,
  gender,
  country,
  city,
  phone,
  registration_date,
  segment
FROM `{project_id}.{dataset}.clients_raw`
WHERE 1=0; -- Create empty schema only

ALTER TABLE `{project_id}.{dataset}.clients` 
  SET OPTIONS (
    description = "Client master data with demographics and registration info",
    labels = [("domain", "customer"), ("pii", "true")]
  );

-- ============================================================================
-- 2. PRODUCTS TABLE (No partition - small dimension)
-- ============================================================================

CREATE OR REPLACE TABLE `{project_id}.{dataset}.products`
OPTIONS (
  description = "Product catalog with categories and pricing",
  labels = [("domain", "product"), ("type", "dimension")]
) AS
SELECT
  product_id,
  product_name,
  category,
  unit_price,
  stock
FROM `{project_id}.{dataset}.products_raw`
WHERE 1=0; -- Create empty schema only

-- ============================================================================
-- 3. ORDERS TABLE
-- ============================================================================

CREATE OR REPLACE TABLE `{project_id}.{dataset}.orders`
PARTITION BY DATE(order_date)
CLUSTER BY status, region
OPTIONS (
  description = "Customer orders with status and payment method",
  labels = [("domain", "order"), ("timeseries", "true")]
) AS
SELECT
  order_id,
  client_id,
  order_date,
  status,
  payment_method,
  region,
  total_amount
FROM `{project_id}.{dataset}.orders_raw`
WHERE 1=0; -- Create empty schema only

-- ============================================================================
-- 4. ORDER_ITEMS TABLE
-- ============================================================================

CREATE OR REPLACE TABLE `{project_id}.{dataset}.order_items`
PARTITION BY DATE(order_date)
CLUSTER BY product_id
OPTIONS (
  description = "Line items within orders (fact table)",
  labels = [("domain", "order"), ("type", "fact")]
) AS
SELECT
  item_id,
  order_id,
  product_id,
  quantity,
  unit_price,
  order_date
FROM `{project_id}.{dataset}.order_items_raw`
WHERE 1=0; -- Create empty schema only

-- ============================================================================
-- 5. INCIDENTS TABLE
-- ============================================================================

CREATE OR REPLACE TABLE `{project_id}.{dataset}.incidents`
PARTITION BY DATE(report_date)
CLUSTER BY category, priority
OPTIONS (
  description = "Customer support incidents and complaints",
  labels = [("domain", "support"), ("timeseries", "true")]
) AS
SELECT
  incident_id,
  client_id,
  report_date,
  category,
  order_id,
  status,
  priority,
  resolution_time_h
FROM `{project_id}.{dataset}.incidents_raw`
WHERE 1=0; -- Create empty schema only

-- ============================================================================
-- 6. PAGE_VIEWS TABLE
-- ============================================================================

CREATE OR REPLACE TABLE `{project_id}.{dataset}.page_views`
PARTITION BY DATE(event_datetime)
CLUSTER BY page, device
OPTIONS (
  description = "User session page views and engagement",
  labels = [("domain", "web"), ("timeseries", "true")]
) AS
SELECT
  session_id,
  client_id,
  page,
  event_datetime,
  duration_seconds,
  device,
  browser,
  traffic_source
FROM `{project_id}.{dataset}.page_views_raw`
WHERE 1=0; -- Create empty schema only

-- ============================================================================
-- DIAGNOSTIC QUERIES
-- ============================================================================

-- Check row counts per table (with partition filters for safety)
SELECT
  'clients' as table_name,
  COUNT(*) as row_count
FROM `{project_id}.{dataset}.clients`
WHERE DATE(registration_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
UNION ALL
SELECT 'products', COUNT(*) FROM `{project_id}.{dataset}.products`
UNION ALL
SELECT 'orders', COUNT(*) FROM `{project_id}.{dataset}.orders`
WHERE DATE(order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
UNION ALL
SELECT 'order_items', COUNT(*) FROM `{project_id}.{dataset}.order_items`
WHERE DATE(order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
UNION ALL
SELECT 'incidents', COUNT(*) FROM `{project_id}.{dataset}.incidents`
WHERE DATE(report_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
UNION ALL
SELECT 'page_views', COUNT(*) FROM `{project_id}.{dataset}.page_views`
WHERE DATE(event_datetime) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY);
