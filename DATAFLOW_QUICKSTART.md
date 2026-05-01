# Dataflow ETL - Quick Start Guide

## 11 Essential Steps to Activate Dataflow (Do It Alone)

### Phase 1: GCP Setup (15 minutes)

#### **STEP 1: Enable Required APIs**
```bash
export PROJECT_ID="your-gcp-project-id"

gcloud services enable dataflow.googleapis.com \
  --project=${PROJECT_ID}
  
gcloud services enable compute.googleapis.com \
  --project=${PROJECT_ID}
  
gcloud services enable bigquery.googleapis.com \
  --project=${PROJECT_ID}
  
gcloud services enable storage-api.googleapis.com \
  --project=${PROJECT_ID}
```

**Verify:**
```bash
gcloud services list --enabled --project=${PROJECT_ID} | grep -E "dataflow|compute|bigquery"
```

---

#### **STEP 2: Create Staging Buckets**
```bash
export BUCKET="dataflow-staging-${PROJECT_ID}"
export REGION="europe-west1"

# Create staging bucket
gsutil mb -p ${PROJECT_ID} -l ${REGION} gs://${BUCKET}

# Create temp subdirectory
gsutil cp gs://null /dev/null  # Dummy operation
```

**Verify:**
```bash
gsutil ls -p ${PROJECT_ID}
```

---

#### **STEP 3: Grant Permissions to Service Account**
```bash
export PROJECT_ID="your-project-id"
export SERVICE_ACCOUNT="ecommerce-pipeline@${PROJECT_ID}.iam.gserviceaccount.com"

# Add roles
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/dataflow.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/dataflow.worker"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/bigquery.dataEditor"
```

---

### Phase 2: Local Setup (5 minutes)

#### **STEP 4: Install Apache Beam with Dataflow Support**
```bash
pip install apache-beam[gcp]==2.53.0
pip install google-cloud-bigquery
pip install google-cloud-storage
pip install python-dotenv
```

**Verify:**
```bash
python -c "import apache_beam; print(apache_beam.__version__)"
```

---

#### **STEP 5: Configure .env File**
Create/update `.env` in project root:
```env
PROJECT_ID=your-gcp-project-id
REGION=europe-west1
DATASET=ecommerce_analytics
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
DATAFLOW_STAGING_BUCKET=gs://dataflow-staging-${PROJECT_ID}
DATAFLOW_TEMP_BUCKET=gs://dataflow-staging-${PROJECT_ID}/temp
DATAFLOW_REGION=europe-west1
INPUT_DATA=gs://your-bucket/data/orders.csv
```

---

#### **STEP 6: Authenticate with GCP**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
gcloud config set project ${PROJECT_ID}
gcloud auth application-default login
```

---

### Phase 3: Data Preparation (5 minutes)

#### **STEP 7: Upload Data to GCS**
```bash
export BUCKET="gs://dataflow-staging-${PROJECT_ID}"

# Upload raw data
gsutil cp data/raw/orders.csv ${BUCKET}/data/orders.csv

# Verify
gsutil ls ${BUCKET}/data/
```

---

#### **STEP 8: Create BigQuery Tables**
```bash
export PROJECT_ID="your-project-id"
export DATASET="ecommerce_analytics"

# Create dataset
bq mk --project_id=${PROJECT_ID} ${DATASET}

# Create output table (auto-schema)
bq mk --table \
  --project_id=${PROJECT_ID} \
  ${DATASET}.orders_processed \
  processed_timestamp:TIMESTAMP,pipeline_version:STRING

# Create error table
bq mk --table \
  --project_id=${PROJECT_ID} \
  ${DATASET}.orders_errors \
  error_timestamp:TIMESTAMP,validation_error:STRING
```

---

### Phase 4: Deploy to Dataflow (5 minutes)

#### **STEP 9: Submit Pipeline to Dataflow**

**Option A: Using provided script (Easiest)**
```bash
# Make script executable
chmod +x beam/submit_to_dataflow.sh

# Submit with defaults
bash beam/submit_to_dataflow.sh

# Or with custom settings
bash beam/submit_to_dataflow.sh \
  --input gs://your-bucket/data/orders.csv \
  --workers 2 \
  --machine-type n1-standard-2
```

**Option B: Manual submission**
```bash
export PROJECT_ID="your-project-id"
export REGION="europe-west1"
export BUCKET="gs://dataflow-staging-${PROJECT_ID}"

python beam/dataflow_etl_pipeline.py \
  --project=${PROJECT_ID} \
  --region=${REGION} \
  --runner=DataflowRunner \
  --staging_location=${BUCKET}/staging \
  --temp_location=${BUCKET}/temp \
  --num_workers=2 \
  --machine_type=n1-standard-2 \
  --input=${BUCKET}/data/orders.csv \
  --output_table=${PROJECT_ID}:ecommerce_analytics.orders_processed \
  --error_table=${PROJECT_ID}:ecommerce_analytics.orders_errors
```

---

### Phase 5: Monitor & Verify (Ongoing)

#### **STEP 10: Monitor Job Execution**

**View all jobs:**
```bash
gcloud dataflow jobs list \
  --project=${PROJECT_ID} \
  --region=${DATAFLOW_REGION}
```

**Get specific job details:**
```bash
export JOB_ID="your-job-id"

gcloud dataflow jobs describe ${JOB_ID} \
  --project=${PROJECT_ID} \
  --region=${DATAFLOW_REGION}
```

**View logs:**
```bash
gcloud logging read \
  "resource.type=dataflow_step AND labels.job_id=${JOB_ID}" \
  --limit=50 \
  --project=${PROJECT_ID}
```

**Monitor in Cloud Console (Best Option):**
```
https://console.cloud.google.com/dataflow/jobs?project=YOUR_PROJECT_ID
```

---

#### **STEP 11: Verify Results**

**Query output table:**
```bash
bq query --use_legacy_sql=false "
SELECT 
  COUNT(*) as total_records,
  COUNT(DISTINCT client_id) as unique_clients,
  MAX(processed_timestamp) as latest_processed
FROM \`${PROJECT_ID}.ecommerce_analytics.orders_processed\`
LIMIT 10
"
```

**Check error table:**
```bash
bq query --use_legacy_sql=false "
SELECT 
  COUNT(*) as error_count,
  validation_error,
  COUNT(DISTINCT validation_error) as unique_errors
FROM \`${PROJECT_ID}.ecommerce_analytics.orders_errors\`
GROUP BY validation_error
"
```

---

## Troubleshooting

### Problem: "Dataflow API not enabled"
```bash
gcloud services enable dataflow.googleapis.com --project=${PROJECT_ID}
```

### Problem: "Permission denied" on GCS
```bash
gsutil iam ch serviceAccount:${SERVICE_ACCOUNT}:objectAdmin gs://${BUCKET}
```

### Problem: "BigQuery table not found"
```bash
bq ls -d --project_id=${PROJECT_ID}
bq ls --project_id=${PROJECT_ID} ${DATASET}
```

### Problem: "Python version mismatch"
```bash
python --version  # Check version (need 3.11+)
pip install --upgrade apache-beam[gcp]
```

### Problem: "Staging bucket permission denied"
```bash
gsutil iam ch serviceAccount:${SERVICE_ACCOUNT}:admin gs://${BUCKET}
```

---

## Common Commands Cheat Sheet

| Task | Command |
|------|---------|
| List jobs | `gcloud dataflow jobs list --region=REGION --project=PROJECT` |
| Get job status | `gcloud dataflow jobs describe JOB_ID --region=REGION` |
| Cancel job | `gcloud dataflow jobs cancel JOB_ID --region=REGION` |
| View metrics | `gcloud dataflow jobs show-metrics JOB_ID --region=REGION` |
| Query results | `bq query "SELECT * FROM PROJECT:DATASET.TABLE LIMIT 10"` |
| Upload data | `gsutil cp local/file.csv gs://bucket/file.csv` |
| Create bucket | `gsutil mb -l REGION gs://bucket-name` |

---

## Performance Tips

### Optimize Worker Configuration
```bash
# For small jobs (< 100GB):
--num_workers=2 --machine_type=n1-standard-2

# For medium jobs (100GB - 1TB):
--num_workers=4 --machine_type=n1-standard-4

# For large jobs (> 1TB):
--num_workers=8 --machine_type=n1-standard-8
```

### Enable Autoscaling
```bash
--autoscaling_algorithm=THROUGHPUT_BASED \
--max_num_workers=10 \
--num_workers=2
```

### Use Spot VMs (80% cheaper)
```bash
--use_public_ips \
--worker_machine_type=n1-standard-2 \
--experiments=use_managed_instance_groups
```

---

## Costs (Estimated for free tier)

| Item | Cost |
|------|------|
| 2 x n1-standard-2 workers, 1 hour | ~$0.10 |
| Data transfer (first 100GB/month) | Free (Free Tier) |
| BigQuery storage (first 1GB/month) | Free (Free Tier) |
| Cloud Storage | Free tier eligible |

**Total for small pipeline:** ~$0

---

## What Happens Now

After submission (STEP 9):

1. ✅ Dataflow creates a job and assigns a Job ID
2. ✅ Worker VMs are provisioned (~2-3 minutes)
3. ✅ Your pipeline code is distributed to workers
4. ✅ Data processing begins (parallel execution)
5. ✅ Results are written to BigQuery
6. ✅ Workers are terminated (you're charged only for execution time)
7. ✅ Job completes (check status in Cloud Console)

---

## Next Steps

After Dataflow is working:

1. **Schedule automatically:** Use Cloud Scheduler to run pipeline daily
2. **Real-time streaming:** Switch to Pub/Sub source instead of GCS
3. **Add monitoring:** Set up alerts for job failures
4. **Optimize costs:** Use autoscaling and spot VMs
5. **Visualize results:** Connect Looker Studio to BigQuery

---

## Support Resources

- [Apache Beam Documentation](https://beam.apache.org/)
- [Google Cloud Dataflow Documentation](https://cloud.google.com/dataflow/docs)
- [BigQuery ETL Patterns](https://cloud.google.com/bigquery/docs/patterns-patterns-common-tasks)
- [Dataflow Job Status](https://console.cloud.google.com/dataflow/jobs)

