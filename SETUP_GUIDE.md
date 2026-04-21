# E-Commerce GCP Analytics Pipeline - SETUP GUIDE

## Current Status
✅ Project scaffolding complete (23 files, 4,400+ lines of code)  
✅ Git repository initialized with 3 commits  
⏳ Python dependencies installing (`pip install -r requirements.txt`)

---

## Pre-Flight Checklist

### 1. **GCP Project Setup** (10 minutes)
- [ ] Create a new GCP project: https://console.cloud.google.com/projectcreate
- [ ] Note your **Project ID** (e.g., `ecommerce-494010`)
- [ ] Create a service account: Console → IAM & Admin → Service Accounts → Create Service Account
  - Service Account Name: `ecommerce-pipeline`
  - Grant these roles:
    - ✅ BigQuery Data Editor
    - ✅ Storage Object Creator
    - ✅ Pub/Sub Admin
    - ✅ Cloud Functions Developer
    - ✅ Cloud Scheduler Admin
    - ✅ Logs Admin (for alerts)
- [ ] Create and download JSON key: Service Account → Keys → Add Key → JSON
- [ ] Save the JSON file locally (you'll reference it in `.env`)

### 2. **Configure Environment** (5 minutes)
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your values
# nano .env  (or use VSCode)
```

**Required `.env` variables:**
```bash
PROJECT_ID=your-gcp-project-id
REGION=europe-west1
DATASET=ecommerce_analytics
BUCKET=ecommerce-${PROJECT_ID}
PUBSUB_TOPIC=orders-realtime
PUBSUB_SUB=orders-realtime-sub
PUBSUB_TOPIC_DLQ=orders-realtime-dlq
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
LOG_LEVEL=INFO
```

### 3. **Verify Setup** (2 minutes)
```bash
# Check Python version
python --version  # Should be 3.11+

# Check gcloud is authenticated
gcloud auth list

# Test BigQuery access
bq --version
```

---

## Execution Phase (Once Dependencies Install)

### Sequential Steps (11 total, ~30-45 minutes)

**STEP 1: Generate Synthetic Data** (2-3 min)
```bash
python scripts/generate_data.py
# Generates 70k+ rows across 6 datasets
# Output: data/raw/*.csv
```
✅ Git commit: `data(generation): generate 70k synthetic rows with Faker and consistent FK relations`

---

**STEP 2: Clean & Validate Data** (1-2 min)
```bash
python scripts/prepare_data.py
# Cleans data quality issues
# Output: data/clean/*_clean.csv, docs/cleaning_report.txt
```
✅ Git commit: `data(cleaning): clean and validate all 6 datasets with quality report`

---

**STEP 3: Setup GCP Infrastructure** (3-5 min)
```bash
# PREVIEW first (safe, no changes)
bash deploy/setup_gcp.sh --dry-run

# Then EXECUTE
bash deploy/setup_gcp.sh
# Creates: GCS bucket, Pub/Sub topics, BigQuery dataset
```
✅ Git commit: `infra(gcp): set up GCS buckets, Pub/Sub topics and BigQuery dataset within free tier`

---

**STEP 4: Create BigQuery Tables & Views** (2-3 min)
```bash
# Run SQL files in order
bq query --use_legacy_sql=false < sql/01_create_tables.sql
# Wait for completion...

bq query --use_legacy_sql=false < sql/02_create_views.sql
# Wait for completion...

# Save advanced queries for later exploration:
# sql/03_advanced_analytics.sql (5 complex queries)
# sql/04_scheduled_queries.sql (2 lightweight jobs)
```
✅ Git commit: `data(bigquery): create 6 tables with partitioning and 7 analytical views`

---

**STEP 5: Load Data to BigQuery** (1-2 min)
```bash
python scripts/load_to_bq.py
# Loads cleaned CSVs to BigQuery tables
# Output: Load validation report
```
✅ Git commit: `feat(bigquery): load all 6 tables and run post-load row count validation`

---

**STEP 6: Deploy Cloud Function** (2-3 min)
```bash
bash deploy/deploy_function.sh
# Deploys GCS-triggered Cloud Function
```
✅ Git commit: `feat(functions): GCS-triggered Cloud Function with DLQ and cost-safe config`

---

**STEP 7: Simulate Real-Time Stream** (3-5 min)
```bash
python scripts/simulate_realtime.py --limit 200
# Publishes 200 sample order events to Pub/Sub
```
✅ Git commit: `feat(pubsub): real-time stream simulator with default 200-message cap`

---

**STEP 8: Run Apache Beam Pipeline** (2-3 min)
```bash
python beam/pipeline.py --limit 100
# Processes Pub/Sub messages locally (DirectRunner)
# Writes to BigQuery valid/error tables
```
✅ Git commit: `feat(beam): local DirectRunner pipeline Pub/Sub pull to BigQuery batch load`

---

**STEP 9: Setup Cloud Scheduler** (2-3 min)
```bash
bash deploy/setup_scheduler.sh
# Creates 3 scheduled jobs (within free tier limit):
# 1. Daily KPI refresh (06:00 UTC)
# 2. Weekly export (Monday 07:00 UTC)
# 3. Monthly cleanup (1st @ 03:00 UTC)
```
✅ Git commit: `infra(scheduler): configure exactly 3 Cloud Scheduler jobs within free tier`

---

**STEP 10: Setup Monitoring & Alerts** (1-2 min)
```bash
python monitoring/setup_alerts.py
# Creates log-based alerts (free - not metric-based):
# - Cloud Function errors
# - Pub/Sub DLQ messages
```
✅ Git commit: `feat(monitoring): cost-free log-based alerts setup`

---

**STEP 11: Final Health Check** (1 min)
```bash
python monitoring/health_check.py
# Verifies pipeline health:
# - BigQuery table row counts
# - Pub/Sub subscription backlog
# - Cloud Function errors
# - Per-component status
```
✅ Git commit: `docs(monitoring): add final health check and status verification`

---

## Cost Guarantee: $0/month

✅ All resources use **GCP Free Tier**:
- BigQuery: 10 GB storage + 1 TB queries/month
- Cloud Storage: 5 GB/month
- Pub/Sub: 10 GB/month (10k topics × 1GB each)
- Cloud Functions: 2M invocations/month
- Cloud Scheduler: 3 jobs/month
- **DirectRunner**: Runs entirely on your local machine ($0 compute)

**NEVER enable**: Dataflow, Compute Engine, Cloud Run, Cloud SQL

---

## Monitoring & Verification

After Step 11, you can explore your data:

### View BigQuery Tables
```bash
# List tables
bq ls -t ecommerce_analytics

# Query top revenue by region
bq query --use_legacy_sql=false < sql/02_create_views.sql
# Then: SELECT * FROM ecommerce_analytics.v_revenue_by_region LIMIT 10;

# Check row counts
bq query --use_legacy_sql=false "SELECT COUNT(*) as row_count FROM ecommerce_analytics.clients;"
```

### Check Pub/Sub
```bash
# View topic info
gcloud pubsub topics describe orders-realtime

# Check subscription backlog
gcloud pubsub subscriptions describe orders-realtime-sub
```

### View Cloud Function Logs
```bash
gcloud functions describe process_upload-gen2 --gen2 --region=europe-west1

# View recent logs
gcloud logging read "resource.type=cloud_function" --limit 10 --format=json
```

---

## Troubleshooting

### Pip Install Issues
- If `pip install` times out: Install packages individually
  ```bash
  pip install faker==24.0.0 pandas==2.2.0 numpy==1.26.4
  pip install google-cloud-bigquery google-cloud-storage google-cloud-pubsub
  ```

### GCP Authentication Fails
- Verify service account JSON path in `.env`: 
  ```bash
  test -f ${GOOGLE_APPLICATION_CREDENTIALS} && echo "✅ File found" || echo "❌ File not found"
  ```
- Test gcloud auth:
  ```bash
  gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
  gcloud config set project ${PROJECT_ID}
  ```

### BigQuery Load Fails
- Check dataset exists:
  ```bash
  bq ls -d | grep ecommerce_analytics
  ```
- Check file exists in GCS:
  ```bash
  gsutil ls gs://${BUCKET}/clean/
  ```

### Cloud Function Deploy Fails
- Check region format:
  ```bash
  gcloud functions list --regions=europe-west1
  ```
- View deployment logs:
  ```bash
  gcloud functions describe process_upload-gen2 --gen2 --region=europe-west1 --log-verbosity=debug
  ```

---

## Key Design Decisions

| Component | Why This Choice | Cost Impact |
|-----------|-----------------|------------|
| **DirectRunner** | Local processing, simpler than Dataflow | $0 vs $0.25/vCPU-hour |
| **Pub/Sub (batch pull)** | Simpler than streaming subscribers | Same cost, easier to manage |
| **BigQuery partitioning** | Filter by date to reduce bytes scanned | 30-50% cost reduction |
| **Cloud Functions (gen2)** | Serverless, auto-scaling | 2M free invocations/month |
| **Log-based alerts** | Free vs metric-based (Cloud Monitoring) | $0 vs $0.02588/alert/month |
| **256MB Cloud Function** | Adequate for data processing | Saves quota vs 512MB |

---

## Documentation

- **`README.md`** - Quick start and execution guide
- **`docs/architecture.md`** - System design with cost justification
- **`docs/sql_explained.md`** - All queries explained in English + French
- **`SETUP_GUIDE.md`** - This file

---

## Next Steps

1. ⏳ **Wait for pip install to complete** (Terminal: `4b440985-aa8e-46ee-9397-8f73ddb3d4d1`)
   - Check status: `python --version`

2. 📋 **Follow Pre-Flight Checklist above** (GCP setup, `.env` file)

3. 🚀 **Execute 11-step pipeline** in order

4. ✅ **Verify** with health check

5. 📊 **Explore data in BigQuery** and create Looker Studio dashboard

---

## Support Resources

- **BigQuery Docs**: https://cloud.google.com/bigquery/docs
- **Pub/Sub Docs**: https://cloud.google.com/pubsub/docs
- **Apache Beam**: https://beam.apache.org/documentation/
- **GCP Free Tier**: https://cloud.google.com/free/docs/free-cloud-features

---

**Project ready for execution!** Once `pip install` completes, start with STEP 1. 🚀
