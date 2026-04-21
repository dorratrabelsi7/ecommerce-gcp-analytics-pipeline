# SQL Guide - Analytical Queries Explained

Tous les requêtes BigQuery are documented here in both English and French for clarity.

## Table of Contents

1. Views (7 analytical views)
2. Advanced Analytics (5 complex queries)
3. Scheduled Queries (2 lightweight queries)

---

## VIEWS (7 ANALYTICAL)

### VIEW 1: v_revenue_by_region

**Objectif commercial (Business Objective):**
Analyser les tendances de chiffre d'affaires par région avec croissance mensuelle (MoM).
Analyze revenue performance by region with month-over-month growth trends.

**Query:**
```sql
WITH regional_revenue AS (
  SELECT
    region,
    DATE_TRUNC(DATE(order_date), MONTH) as month,
    SUM(total_amount) as monthly_revenue,
    COUNT(DISTINCT order_id) as monthly_orders,
    AVG(total_amount) as avg_basket_size
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
  ROUND(100 * monthly_revenue / SUM(monthly_revenue) OVER (PARTITION BY month), 2) as pct_of_global_revenue,
  ROUND(
    100 * (monthly_revenue - LAG(monthly_revenue) OVER (PARTITION BY region ORDER BY month)) 
    / LAG(monthly_revenue) OVER (PARTITION BY region ORDER BY month),
    2
  ) as mom_growth_pct
FROM regional_revenue
ORDER BY month DESC, monthly_revenue DESC;
```

**Explications (Explanations):**
- **WITH regional_revenue:** Agrège les données par région et mois. Groups data by region and month.
- **DATE_TRUNC:** Tronque les dates au début du mois. Truncates dates to month start.
- **WHERE order_date >= DATE_SUB:** Filtre les 13 derniers mois (économise les coûts). Filters to last 13 months (cost-safe).
- **LAG() OVER:** Calcule la croissance mensuelle en comparant aux mois précédents. Calculates MoM growth.
- **Partition columns:** Utilise les colonnes de partition (region) pour l'efficacité. Uses partition columns for efficiency.

**Use Cases:**
- Identify fastest-growing regions
- Detect regional performance trends
- Support regional strategy decisions

---

### VIEW 2: v_inactive_clients

**Objectif commercial:**
Identifier les clients à risque sans achat depuis 60 jours pour les ciblage (réactivation).
Identify at-risk customers with no purchase in 60 days for win-back campaigns.

**Query:** (Complex multi-table join with LEFT OUTER)
```sql
WITH client_order_history AS (
  SELECT
    c.client_id,
    MAX(o.order_date) as last_purchase_date,
    COUNT(DISTINCT o.order_id) as total_orders,
    SUM(o.total_amount) as historical_revenue,
    COUNT(DISTINCT i.incident_id) as incident_count
  FROM `{project_id}.{dataset}.clients` c
  LEFT JOIN `{project_id}.{dataset}.orders` o ON c.client_id = o.client_id
  LEFT JOIN `{project_id}.{dataset}.incidents` i ON c.client_id = i.client_id
  GROUP BY c.client_id, ...
)
SELECT
  ...
  DATE_DIFF(CURRENT_DATE(), CAST(last_purchase_date AS DATE), DAY) as days_inactive
FROM client_order_history
WHERE last_purchase_date < DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
ORDER BY historical_revenue DESC;
```

**Explications:**
- **LEFT JOIN:** Inclut tous les clients même sans commandes. Includes all clients even with zero orders.
- **COALESCE:** Remplace les NULL par 0 pour les calculs. Replaces NULL with 0 for calculations.
- **DATE_DIFF:** Calcule les jours d'inactivité. Calculates days since last purchase.
- **Ordre par historical_revenue DESC:** Les clients les plus rentables en priorité. Sorts by highest-value clients first.

**Use Cases:**
- Win-back campaigns
- Churn risk analysis
- Customer retention strategies

---

### VIEW 3: v_top_products

**Objectif commercial:**
Classer les produits par chiffre d'affaires avec taux d'annulation.
Rank products by revenue with cancellation rates per category.

**Query:**
```sql
WITH product_stats AS (
  SELECT
    p.product_id,
    SUM(oi.quantity * oi.unit_price) as revenue,
    SUM(oi.quantity) as units_sold,
    ROUND(
      100 * COUNTIF(o.status = 'Cancelled') / COUNT(DISTINCT o.order_id),
      2
    ) as cancellation_rate,
    RANK() OVER (PARTITION BY p.category ORDER BY revenue DESC) as rank_in_category
  FROM `{project_id}.{dataset}.products` p
  LEFT JOIN `{project_id}.{dataset}.order_items` oi ON p.product_id = oi.product_id
  LEFT JOIN `{project_id}.{dataset}.orders` o ON oi.order_id = o.order_id
  GROUP BY p.product_id, p.category
)
SELECT * FROM product_stats
WHERE revenue > 0
ORDER BY category, revenue DESC;
```

**Explications:**
- **RANK() OVER (PARTITION BY category):** Classe chaque produit dans sa catégorie. Ranks products within each category.
- **COUNTIF:** Compte les commandes avec status 'Cancelled'. Counts cancelled orders.
- **WHERE revenue > 0:** Exclut les produits sans ventes. Filters out unsold products.

---

### VIEW 4: v_recurring_incidents

**Objectif commercial:**
Analyser la qualité du support par catégorie d'incident.
Analyze support quality metrics by incident category.

**Query:**
```sql
SELECT
  i.category,
  COUNT(DISTINCT i.incident_id) as incident_count,
  ROUND(AVG(CAST(i.resolution_time_h AS FLOAT64)), 1) as avg_resolution_hours,
  ROUND(100 * COUNTIF(i.status = 'Escalated') / COUNT(*), 2) as escalation_rate,
  ROUND(100 * COUNTIF(i.priority = 'Critical') / COUNT(*), 2) as critical_rate,
  ROUND(100 * COUNTIF(i.order_id IS NOT NULL) / COUNT(*), 2) as pct_linked_to_order
FROM `{project_id}.{dataset}.incidents` i
WHERE i.report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
GROUP BY i.category
ORDER BY incident_count DESC;
```

**Explications:**
- **COUNTIF:** Calcule les taux (escalade, critique). Calculates percentage rates.
- **AVG(CAST ... AS FLOAT64):** Convertit en float pour division précise. Converts to float for accurate division.
- **WHERE report_date >= DATE_SUB:** Filtre les 12 derniers mois. Partition-filtered to last year.

---

### VIEW 5: v_navigation_funnel

**Objectif commercial:**
Mesurer l'engagement utilisateur par page et préférence appareil.
Measure user engagement by page and device preference.

**Query:**
```sql
SELECT
  page,
  COUNT(DISTINCT session_id) as session_count,
  ROUND(AVG(CAST(duration_seconds AS FLOAT64)), 1) as avg_duration_seconds,
  COUNT(DISTINCT client_id) as unique_users,
  ROUND(100 * COUNTIF(device = 'Mobile') / COUNT(*), 2) as pct_mobile,
  ROUND((avg_duration_seconds * session_count / 1000), 2) as engagement_score
FROM `{project_id}.{dataset}.page_views`
WHERE event_datetime >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY page
ORDER BY session_count DESC;
```

**Explications:**
- **COUNT(DISTINCT session_id):** Compte les sessions uniques. Counts unique sessions.
- **engagement_score = (duration * count / 1000):** Formule maison pour l'engagement. Custom formula for engagement ranking.
- **Partition filter:** Les 90 derniers jours (économise coûts). Last 90 days (cost-safe).

---

### VIEW 6: v_weekly_kpis

**Objectif commercial:**
Suivre les indicateurs clés hebdomadaires avec croissance semaine-sur-semaine.
Track weekly KPIs with week-over-week growth trends.

**Query:**
```sql
WITH weekly_stats AS (
  SELECT
    ISO_WEEK(DATE(o.order_date)) as iso_week,
    ISO_YEAR(DATE(o.order_date)) as iso_year,
    SUM(o.total_amount) as weekly_revenue,
    COUNT(DISTINCT o.order_id) as weekly_orders,
    COUNT(DISTINCT i.incident_id) as incident_count
  FROM `{project_id}.{dataset}.orders` o
  LEFT JOIN `{project_id}.{dataset}.incidents` i ON o.client_id = i.client_id
  WHERE o.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
    AND o.status = 'Delivered'
  GROUP BY iso_year, iso_week
)
SELECT
  iso_year,
  iso_week,
  weekly_revenue,
  weekly_orders,
  ROUND(100 * (weekly_revenue - LAG(weekly_revenue) OVER (ORDER BY iso_year, iso_week))
    / LAG(weekly_revenue) OVER (ORDER BY iso_year, iso_week), 2) as wow_growth_pct
FROM weekly_stats
ORDER BY iso_year DESC, iso_week DESC;
```

**Explications:**
- **ISO_WEEK/ISO_YEAR:** Utilise les semaines ISO pour cohérence. Uses ISO weeks for consistency.
- **LAG() OVER:** Calcule WoW growth. Calculates week-over-week percentages.
- **WHERE status = 'Delivered':** Exclut les commandes en attente. Filters to delivered orders only.

---

### VIEW 7: v_client_360

**Objectif commercial:**
Profil client complet avec segmentation par valeur (VIP, Regular, At risk).
Comprehensive customer profile with value-based segmentation.

**Query:** (Most complex - uses window functions and scoring)
```sql
WITH client_profile AS (
  SELECT
    c.client_id,
    ROUND(COALESCE(SUM(o.total_amount), 0), 2) as lifetime_revenue,
    COUNT(DISTINCT o.order_id) as order_count,
    ROUND(COALESCE(AVG(o.total_amount), 0), 2) as avg_basket_size,
    COUNT(DISTINCT i.incident_id) as incident_count,
    COUNT(DISTINCT pv.page) as pages_visited
  FROM clients c
  LEFT JOIN orders o ON c.client_id = o.client_id
  LEFT JOIN incidents i ON c.client_id = i.client_id
  LEFT JOIN page_views pv ON c.client_id = pv.client_id
  GROUP BY c.client_id, ...
)
SELECT
  client_id,
  lifetime_revenue,
  order_count,
  incident_count,
  ROUND(
    lifetime_revenue * 0.5 
    + (20.0 / NULLIF(CAST(incident_count AS FLOAT64), 0))
    + order_count * 2,
    2
  ) as value_score,
  CASE 
    WHEN value_score > 200 THEN 'VIP'
    WHEN value_score BETWEEN 50 AND 200 THEN 'Regular'
    ELSE 'At risk'
  END as value_segment
FROM client_profile
ORDER BY lifetime_revenue DESC;
```

**Formule de score (Scoring Formula):**
```
value_score = revenue × 0.5 + (20 / incident_count) + order_count × 2

- Revenue × 0.5: 50% weight on spending
- 20 / incident_count: Quality bonus (fewer incidents = higher score)
- order_count × 2: 2 points per purchase
```

**Segmentation:**
- **VIP:** score > 200 (high-value, loyal)
- **Regular:** score 50-200 (stable, growth potential)
- **At risk:** score < 50 (low-value or high-issue)

---

## ADVANCED ANALYTICS (5 QUERIES)

### QUERY 1: RFM Segmentation

**Objectif:** Classifier les clients par Recency, Frequency, Monetary (RFM).
Classify customers using the RFM (Recency, Frequency, Monetary) model.

**Résultat:** Champions, Loyal, At Risk, Lost

---

### QUERY 2: Monthly Cohort Analysis

**Objectif:** Suivre la rétention et le chiffre d'affaires par cohorte mensuelle.
Track revenue cohort evolution over 12 months by registration month.

**Résultat:** Cohort retention matrix (month-by-month)

---

### QUERY 3: 4-Week Rolling Revenue Trend

**Objectif:** Identifier les tendances long-terme lissées sur 4 semaines.
Smooth out weekly noise to identify underlying revenue trends.

**Résultat:** Rolling average and variance

---

### QUERY 4: Regional Anomaly Detection

**Objectif:** Détecter les commandes anormalement grandes (outliers).
Identify unusually large orders using statistical z-score (>2 stddev).

**Résultat:** Orders with z-score, classified as high/low anomalies

---

### QUERY 5: Navigation Conversion Funnel

**Objectif:** Mesurer les taux de conversion /products → /cart → /checkout.
Calculate step-by-step conversion rates through the purchase funnel.

**Résultat:** Funnel drop-off rates

---

## SCHEDULED QUERIES (2 LIGHTWEIGHT)

### Scheduled Query 1: Daily KPI Refresh

**Fréquence:** Chaque jour à 06:00 UTC (via Cloud Scheduler)
**Coût estimé:** 1-5 MB scannés

Creates daily aggregated metrics for dashboard refreshes.

### Scheduled Query 2: Weekly RFM Segmentation Update

**Fréquence:** Chaque lundi à 07:00 UTC
**Coût estimé:** 10-20 MB scannés

Updates customer RFM segments weekly for campaign targeting.

---

## COST OPTIMIZATION TIPS

✅ **Always filter on partition columns:**
```sql
WHERE DATE(order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
```

✅ **Use LIMIT on exploratory queries:**
```sql
SELECT * FROM huge_table LIMIT 1000
```

✅ **Cluster by filter columns:**
- Clusters reduce bytes scanned within partitions
- Example: orders clustered by `status` + `region`

✅ **Avoid SELECT ***
```sql
-- Good (only needed columns)
SELECT order_id, client_id, total_amount FROM orders

-- Expensive (reads everything)
SELECT * FROM orders
```

✅ **Use approximate functions when possible:**
```sql
-- Cheap approximate
SELECT APPROX_QUANTILES(amount, 100)[OFFSET(50)] FROM orders

-- Expensive exact
SELECT PERCENTILE_CONT(amount, 0.5) FROM orders
```

---

**Author:** Dorra Trabelsi  
**Date:** 2026-04-21  
**Language:** English + Français
