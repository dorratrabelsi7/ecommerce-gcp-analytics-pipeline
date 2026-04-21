# Architecture: Cloud-Native E-commerce Analytics Pipeline

## System Overview

This document describes the technical architecture of the GCP e-commerce analytics pipeline, with justification for design choices and cost optimization strategies.

```
Synthetic Data Generation
  ↓
Data Cleaning & Validation
  ↓
Cloud Storage (GCS)
  ↓
BigQuery (Analytics Database)
  ↓
Pub/Sub (Event Stream)
  ↓
Apache Beam (DirectRunner - Local Processing)
  ↓
BigQuery (Stream Ingestion)
  ↓
Looker Studio (BI Dashboards)
```

## Component Architecture

### 1. Data Generation Layer

**Technology:** Python + Faker + Pandas + NumPy

**Purpose:**
- Generate 70,000+ synthetic rows with realistic business relationships
- Create 5 interconnected datasets (clients, products, orders, incidents, sessions)
- Simulate 2.5+ years of transaction history

**Why local generation?**
- ✅ $0 cost (runs on your machine)
- ✅ No external APIs or services needed
- ✅ Deterministic (seeded randomness for reproducibility)
- ✅ Fast iteration for testing

**Constraints enforced:**
- Foreign key relationships (orders.client_id → clients.client_id)
- Date consistency (orders only after client registration)
- Category-based pricing (Electronics > Accessories)
- Realistic distributions (bimodal web traffic patterns)

---

### 2. Data Cleaning & Validation

**Technology:** Python + Pandas + Python logging

**Purpose:**
- Remove duplicates and NULL values in key columns
- Fix malformed email addresses
- Parse dates to proper datetime types
- Round monetary values to 2 decimal places
- Recompute order totals as source of truth

**Data Quality Issues Handled:**
- 2% injected NULLs → removed
- 1% duplicate rows → deduplicated
- 0.5% malformed emails ("at" instead of "@") → fixed
- 0.3% invalid ages (< 10 or > 100) → removed

**Output:**
- 6 cleaned CSV files: `*_clean.csv`
- Cleaning report with metrics

---

### 3. Cloud Storage (GCS)

**Technology:** Google Cloud Storage

**Tier:** Free (5 GB/month limit)

**Usage:**
- Store cleaned CSV files in structured buckets:
  - `gs://ecommerce-raw-{PROJECT_ID}/raw/clients/`
  - `gs://ecommerce-raw-{PROJECT_ID}/raw/orders/`
  - etc.
- Version control enabled for safety
- Triggers Cloud Function on file finalize

**Cost:** ~20 MB / 5 GB free = ✅ Within free tier

---

### 4. BigQuery (Analytics Database)

**Technology:** Google BigQuery

**Tier:** Free (1 TB queries/month, 10 GB storage/month)

**Schema Design:**

```
Tables:
├─ clients (2,000 rows)
│  └─ Partitioned: DATE(registration_date)
│  └─ Clustered: country, segment
├─ products (50 rows)
│  └─ No partition (small dimension table)
├─ orders (15,000 rows)
│  └─ Partitioned: DATE(order_date)
│  └─ Clustered: status, region
├─ order_items (45,000+ rows)
│  └─ Partitioned: DATE(order_date)
│  └─ Clustered: product_id
├─ incidents (3,000 rows)
│  └─ Partitioned: DATE(report_date)
│  └─ Clustered: category, priority
└─ page_views (50,000 rows)
   └─ Partitioned: DATE(event_datetime)
   └─ Clustered: page, device
```

**Why Partitioning & Clustering?**
- Reduces bytes scanned per query
- Queries filtered on date columns → massive cost savings
- Example: `WHERE DATE(order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)` scans only latest partition

**7 Analytical Views:**
1. `v_revenue_by_region` - Regional revenue trends with MoM growth
2. `v_inactive_clients` - At-risk customers (no purchase in 60 days)
3. `v_top_products` - Product rankings by category
4. `v_recurring_incidents` - Support quality metrics
5. `v_navigation_funnel` - Web engagement by page/device
6. `v_weekly_kpis` - Weekly metrics with week-over-week growth
7. `v_client_360` - Comprehensive customer profiles with value segmentation

**Cost Optimization:**
- All views filter on partition columns → ~100 MB/month queries
- Scheduled queries only run nightly (not continuous)

---

### 5. Pub/Sub (Real-Time Event Stream)

**Technology:** Google Cloud Pub/Sub

**Tier:** Free (10 GB/month limit)

**Usage:**
- Topic: `orders-realtime` - incoming simulated orders
- Topic: `orders-realtime-dlq` - dead-letter queue for errors
- Subscription: `orders-sub` - for Beam pipeline consumption

**Message Format:**
```json
{
  "order_id": "ORD00001",
  "client_id": "C0001",
  "total_amount": 127.45,
  "status": "Delivered",
  "sent_at": "2024-04-21T14:32:01Z"
}
```

**Cost:** ~50 KB / 10 GB free = ✅ Negligible cost

---

### 6. Apache Beam (DirectRunner)

**Technology:** Apache Beam with DirectRunner

**Why DirectRunner instead of Dataflow?**

| Feature | Dataflow | DirectRunner |
|---------|----------|--------------|
| **Cost** | $0.25 per vCPU-hour | **$0** |
| **Scaling** | Serverless (auto-scale) | Single machine |
| **Setup** | Complex | Simple (one command) |
| **For this project size** | Overkill | Perfect fit |

**Pipeline Steps:**
```
1. Pull messages from Pub/Sub (batch pull - not streaming)
2. Parse JSON and validate required fields
3. Enrich with processing_timestamp
4. Write valid → BigQuery table (orders_stream)
5. Write invalid → BigQuery table (pipeline_errors)
```

**Why Batch Pull Instead of Streaming?**
- Simpler (easier to stop and debug)
- Batch-oriented workload (nightly refresh)
- No streaming costs

---

### 7. Cloud Functions

**Technology:** Google Cloud Functions (gen2, Python 3.11)

**Tier:** Free (2M invocations/month)

**Trigger:** GCS file finalize event

**Functionality:**
- Detects uploaded CSV files
- Maps filename to BigQuery table
- Loads CSV data with error handling
- Publishes confirmation to Pub/Sub
- Routes errors to dead-letter queue

**Why GCS Trigger?**
- Automatic (no polling)
- Serverless
- Scales to zero

**Cost:** < 100 invocations/month × 256 MB = ✅ Free tier

---

### 8. Cloud Scheduler

**Technology:** Google Cloud Scheduler

**Tier:** Free (3 jobs/month limit)

**Jobs:**
| Job | Schedule | Action |
|-----|----------|--------|
| `daily-bq-refresh` | Every day 06:00 UTC | Refresh KPI tables |
| `weekly-kpi-export` | Every Monday 07:00 UTC | Export weekly report |
| `monthly-cleanup` | 1st of month 03:00 UTC | Delete old partitions |

**Why Pub/Sub?**
- Triggers downstream Cloud Functions
- Decouples scheduling from processing
- Enables error handling via DLQ

**Cost:** 3 jobs/month × $0 = ✅ Free tier

---

### 9. Cloud Logging & Monitoring

**Technology:** Cloud Logging (free tier)

**Monitoring:**
- Log-based alerts (free) NOT metric-based (costly)
- Health check script uses gcloud CLI
- No Cloud Monitoring API calls

**What We Track:**
- Cloud Function execution times
- BigQuery query errors
- Pub/Sub delivery failures
- Pipeline error rates

**Cost:** $0 (logs are free up to 50 GB/month)

---

### 10. Looker Studio (BI & Visualization)

**Technology:** Google Looker Studio

**Purpose:**
- Connect to BigQuery views
- Create interactive dashboards
- Share reports with stakeholders

**Cost:** Always free

---

## Data Flow Diagram

```
1. GENERATION        2. PREPARATION       3. STORAGE
┌─────────────┐      ┌──────────────┐     ┌─────────┐
│   Faker     │─────→│   Pandas     │────→│   GCS   │
│   NumPy     │      │   Cleaning   │     │ Buckets │
│   Pandas    │      │   Logging    │     └────┬────┘
└─────────────┘      └──────────────┘          │
                                               ↓
4. INITIAL LOAD                          5. STREAM INGESTION
┌─────────────────────────────────┐     ┌──────────────┐
│  BigQuery                       │────→│  Pub/Sub     │
│ ├─ Tables (6x)                 │     │ ├─ Topic     │
│ ├─ Partitioned + Clustered     │     │ └─ DLQ       │
│ └─ 7 Analytical Views           │     └──────┬───────┘
└─────────────────────────────────┘            │
                  ↑                             ↓
                  │                    ┌──────────────────┐
                  │                    │  Apache Beam     │
                  │                    │  (DirectRunner)  │
                  │                    └────────┬─────────┘
                  │                             │
                  └─────────────────────────────┘
                                               │
                                               ↓
6. VISUALIZATION
┌──────────────────────┐
│  Looker Studio       │
│  ├─ Dashboards      │
│  ├─ Reports         │
│  └─ KPI Cards       │
└──────────────────────┘
```

---

## Cost Breakdown

### Estimated Monthly Costs

| Service | Free Tier | Usage | Cost |
|---------|-----------|-------|------|
| **BigQuery Storage** | 10 GB | ~50 MB | ✅ $0 |
| **BigQuery Queries** | 1 TB | ~100 MB | ✅ $0 |
| **Cloud Storage** | 5 GB | ~20 MB | ✅ $0 |
| **Cloud Functions** | 2M invokes | < 100 | ✅ $0 |
| **Pub/Sub** | 10 GB | ~50 KB | ✅ $0 |
| **Cloud Scheduler** | 3 jobs | 3 jobs | ✅ $0 |
| **Looker Studio** | Always free | Dashboard | ✅ $0 |
| **DirectRunner** | N/A (local) | Local machine | ✅ $0 |
| **Cloud Logging** | 50 GB logs | < 1 GB | ✅ $0 |
| | | **TOTAL** | **✅ $0/month** |

### Cost Safety Rules Enforced

✅ Always partition queries on date columns  
✅ Always use LIMIT on exploratory queries  
✅ DirectRunner only (never DataflowRunner)  
✅ No Compute Engine or Cloud Run  
✅ No Cloud SQL  
✅ Stream simulator defaults to 200 messages (not unlimited)  
✅ Health check uses partition filters  

---

## What Would Change in Production?

For a **real production environment** with 1M+ customers:

1. **Dataflow** (not DirectRunner)
   - Auto-scaling streaming pipeline
   - Cost: ~$2-5/day depending on throughput

2. **Cloud Run** (not Cloud Functions)
   - Always-on API endpoints
   - Cost: ~$1-5/day depending on traffic

3. **Cloud SQL** (not BigQuery)
   - Operational database (OLTP)
   - Cost: ~$20-50/day for HA setup

4. **Cloud Dataprep** (advanced data cleaning)
   - Visual ETL interface
   - Cost: ~$0.10 per job execution

5. **Cloud Monitoring** (instead of Cloud Logging)
   - Advanced metrics and alerting
   - Cost: ~$5-20/month

6. **Looker** (instead of Looker Studio)
   - Enterprise BI platform
   - Cost: $10,000+ per year

**Estimated Production Cost: $500-1,500/month**

---

## Deployment Checklist

- ✅ Python 3.11 installed
- ✅ `gcloud` CLI installed and authenticated
- ✅ Service account key created (for local dev)
- ✅ .env file configured with PROJECT_ID
- ✅ Git configured with commit author info
- ✅ Requirements installed: `pip install -r requirements.txt`

## Key Design Principles

| Principle | Implementation |
|-----------|-----------------|
| **Cost-First** | Free tier resources only; DirectRunner locally |
| **Simplicity** | Batch processing, not complex streaming |
| **Observability** | Structured logging everywhere |
| **Reproducibility** | Seeded randomness, versioned infrastructure |
| **Modularity** | Each component independent and testable |
| **Documentation** | Every script has cost notes and docstrings |

---

## References

- [BigQuery Pricing](https://cloud.google.com/bigquery/pricing)
- [Cloud Functions Pricing](https://cloud.google.com/functions/pricing)
- [Pub/Sub Pricing](https://cloud.google.com/pubsub/pricing)
- [Apache Beam](https://beam.apache.org/)
- [DirectRunner](https://beam.apache.org/documentation/runners/direct/)

---

**Author:** Dorra Trabelsi  
**Date:** 2026-04-21  
**Cost:** $0/month (GCP Free Tier)
