-- ============================================================================
-- CREATE BIGQUERY TABLES FOR ECOMMERCE ANALYTICS
-- ============================================================================

CREATE OR REPLACE TABLE ecommerce_analytics.clients (
  client_id INT64,
  last_name STRING,
  first_name STRING,
  email STRING,
  age INT64,
  gender STRING,
  country STRING,
  city STRING,
  phone STRING,
  registration_date DATE,
  segment STRING
)
PARTITION BY DATE(registration_date)
CLUSTER BY country, segment
OPTIONS(
  description = "Client master data with demographics and registration info",
  labels = [("domain", "customer"), ("pii", "true")]
);

-- ============================================================================
-- PRODUCTS TABLE (No partition - small dimension)
-- ============================================================================

CREATE OR REPLACE TABLE ecommerce_analytics.products (
  product_id INT64,
  name STRING,
  category STRING,
  price NUMERIC(10, 2),
  cost NUMERIC(10, 2),
  description STRING,
  created_date DATE,
  stock_quantity INT64
)
OPTIONS(
  description = "Product catalog with pricing and inventory",
  labels = [("domain", "product"), ("materialized", "false")]
);

-- ============================================================================
-- ORDERS TABLE
-- ============================================================================

CREATE OR REPLACE TABLE ecommerce_analytics.orders (
  order_id INT64,
  client_id INT64,
  order_date DATE,
  order_time TIME,
  total_amount NUMERIC(12, 2),
  status STRING,
  country STRING,
  created_timestamp TIMESTAMP
)
PARTITION BY DATE(order_date)
CLUSTER BY client_id, country
OPTIONS(
  description = "Order transactions with amounts and statuses",
  labels = [("domain", "order"), ("pii", "true")]
);

-- ============================================================================
-- ORDER_ITEMS TABLE
-- ============================================================================

CREATE OR REPLACE TABLE ecommerce_analytics.order_items (
  order_item_id INT64,
  order_id INT64,
  product_id INT64,
  quantity INT64,
  unit_price NUMERIC(10, 2),
  line_total NUMERIC(12, 2),
  order_date DATE,
  created_timestamp TIMESTAMP
)
PARTITION BY DATE(order_date)
CLUSTER BY order_id, product_id
OPTIONS(
  description = "Line items for orders with pricing",
  labels = [("domain", "order"), ("materialized", "false")]
);

-- ============================================================================
-- INCIDENTS TABLE (Support tickets)
-- ============================================================================

CREATE OR REPLACE TABLE ecommerce_analytics.incidents (
  incident_id INT64,
  client_id INT64,
  order_id INT64,
  category STRING,
  description STRING,
  priority STRING,
  status STRING,
  report_date DATE,
  resolved_date DATE,
  created_timestamp TIMESTAMP
)
PARTITION BY DATE(report_date)
CLUSTER BY status, priority
OPTIONS(
  description = "Customer support incidents and tickets",
  labels = [("domain", "support"), ("pii", "true")]
);

-- ============================================================================
-- PAGE_VIEWS TABLE (Website analytics)
-- ============================================================================

CREATE OR REPLACE TABLE ecommerce_analytics.page_views (
  page_view_id INT64,
  client_id INT64,
  page_title STRING,
  page_url STRING,
  referrer STRING,
  event_datetime DATETIME,
  event_date DATE,
  session_id STRING,
  device_type STRING,
  created_timestamp TIMESTAMP
)
PARTITION BY DATE(event_date)
CLUSTER BY client_id, page_url
OPTIONS(
  description = "Website page view events and sessions",
  labels = [("domain", "web_analytics"), ("pii", "true")]
);
