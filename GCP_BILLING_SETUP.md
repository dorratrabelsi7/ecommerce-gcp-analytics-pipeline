# 🚀 GCP BILLING & DEPLOYMENT GUIDE

## ⚠️ Current Status: Billing Required

Your GCP project `ecommerce-494010` is configured but requires billing to be activated.

**This is REQUIRED for Free Tier usage** (even though Free Tier is free!).

---

## 📋 Step 1: Enable Billing on GCP Project

### Option A: Via GCP Console (Recommended)
1. Open: https://console.cloud.google.com/billing/linkedaccount?project=ecommerce-494010
2. Click **"Link Billing Account"**
3. If you don't have a billing account:
   - Click **"Create New Billing Account"**
   - Add your payment method (credit/debit card)
   - Complete the setup
4. Select the billing account and click **"Link"**

### Option B: Via gcloud CLI
```bash
# Find your billing account ID
gcloud billing accounts list

# Link billing account to project
gcloud billing projects link ecommerce-494010 \
  --billing-account=YOUR_BILLING_ACCOUNT_ID
```

---

## 📊 Why Billing Is Required

Even though the Free Tier is **completely free**, Google requires:
- A valid billing account
- A valid payment method (credit/debit card)
- To prevent abuse

**Free Tier Guarantees:**
- ✅ $0 cost when within limits
- ✅ 1 TB BigQuery queries/month
- ✅ 5 GB Cloud Storage
- ✅ 10,000 Pub/Sub messages
- ✅ Cloud Functions: 2M free invocations

**Our Pipeline stays under all limits:**
- BigQuery: ~500 MB queries/month
- Storage: ~50 MB
- Pub/Sub: ~500 messages
- Functions: ~100 invocations

---

## 🔧 Step 2: Execute GCP Setup

Once billing is enabled, run:

```powershell
# Activate Python 3.12 venv
.\venv312\Scripts\Activate.ps1

# Create GCS bucket
gsutil mb -l europe-west1 gs://ecommerce-494010-data

# Create BigQuery dataset
bq --project_id=ecommerce-494010 mk \
  --dataset \
  --location=EU \
  ecommerce_analytics

# Create Pub/Sub topic
gcloud pubsub topics create orders-realtime \
  --project=ecommerce-494010

# Create Pub/Sub subscription
gcloud pubsub subscriptions create orders-realtime-sub \
  --topic=orders-realtime \
  --ack-deadline=60 \
  --message-retention-duration=10m \
  --project=ecommerce-494010

# Create DLQ topic
gcloud pubsub topics create orders-realtime-dlq \
  --project=ecommerce-494010
```

---

## 🚀 Step 3: Deploy BigQuery Schema

```powershell
# Run with Python 3.12
.\venv312\Scripts\python.exe scripts/load_to_bq.py

# Or use bq CLI
bq query --use_legacy_sql=false < sql/01_create_tables.sql
bq query --use_legacy_sql=false < sql/02_create_views.sql
```

---

## 📝 Step 4: Continue Pipeline Execution

```powershell
# STEP 4: BigQuery DDL (after tables created)
python scripts/load_to_bq.py

# STEP 5: Stream simulator (publishes to Pub/Sub)
python scripts/simulate_realtime.py --limit 200

# STEP 6: Beam pipeline (processes Pub/Sub messages)
python beam/pipeline.py --limit 100

# STEP 7-10: Cloud Functions, Scheduler, Monitoring
bash deploy/deploy_function.sh
bash deploy/setup_scheduler.sh
python monitoring/setup_alerts.py
python monitoring/health_check.py
```

---

## ✅ Verification Commands

After billing is enabled:

```powershell
# Verify bucket created
gsutil ls -b gs://ecommerce-494010-data

# Verify dataset created
bq ls --dataset_id=ecommerce_analytics

# Verify Pub/Sub topics
gcloud pubsub topics list --project=ecommerce-494010

# Verify tables in BigQuery
bq ls ecommerce_analytics

# View costs (should be $0 for Free Tier)
gcloud billing accounts list
```

---

## 💡 Quick Reference

| Resource | Status | Command |
|----------|--------|---------|
| Project | ✅ Configured | `gcloud config set project ecommerce-494010` |
| APIs | ✅ Enabled | `gcloud services list --enabled` |
| Billing | ⏳ **REQUIRED** | https://console.cloud.google.com/billing |
| GCS Bucket | ⏸️ Pending | `gsutil mb -l europe-west1 gs://ecommerce-494010-data` |
| BigQuery Dataset | ⏸️ Pending | `bq mk --dataset ecommerce_analytics` |
| Pub/Sub Topic | ⏸️ Pending | `gcloud pubsub topics create orders-realtime` |

---

## 🎯 Next Actions

1. **Enable billing on GCP** (5 minutes) → https://console.cloud.google.com/billing/linkedaccount
2. **Run GCP setup commands** (above)
3. **Execute pipeline steps 4-11**
4. **Monitor costs** (will be $0)

---

## ❓ FAQ

**Q: Will this cost money?**
A: No. All services are within the Free Tier limits and $0/month.

**Q: Do I need a credit card?**
A: Yes, for billing account verification. Google won't charge without explicit consent.

**Q: Can I use a different region?**
A: Yes, but change `europe-west1` to your preferred region in `.env` and commands.

**Q: How long does billing activation take?**
A: Usually 5-15 minutes. Then you can run the setup commands.

---

Generated: 2026-04-21
Project: ecommerce-494010
Region: europe-west1
