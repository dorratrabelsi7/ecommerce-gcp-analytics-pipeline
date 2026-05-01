# Google Cloud Dataflow - ETL/ELT Setup Guide

## What is Dataflow?

**Dataflow** is Google Cloud's managed Apache Beam service that runs ETL/ELT pipelines at scale. Unlike DirectRunner (your local machine), Dataflow:
- Runs on GCP infrastructure (auto-scaling workers)
- Handles large datasets efficiently
- Provides monitoring & logging
- Supports both batch and streaming

**Cost Note:** Dataflow charges $0.04-0.10 per vCPU-hour. Free tier covers some resources.

---

## Prerequisites

✅ GCP Project with service account (from SETUP_GUIDE.md)  
✅ `gcloud` CLI installed and authenticated  
✅ Python 3.11+ with Beam installed  
✅ Google Cloud Storage bucket for Dataflow staging  
✅ BigQuery dataset created

---

## STEP 1: Enable Required GCP APIs

### 1a. Enable APIs via Cloud Console
```bash
# Or use gcloud:
gcloud services enable dataflow.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable storage-api.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable pubsub.googleapis.com
```

### 1b. Verify APIs are enabled
```bash
gcloud services list --enabled | grep -E "dataflow|compute|bigquery"
```

---

## STEP 2: Create GCS Bucket for Dataflow

Dataflow needs a staging bucket for temporary files during execution.

```bash
# Set your variables
export PROJECT_ID="your-project-id"
export BUCKET_NAME="dataflow-staging-${PROJECT_ID}"
export REGION="europe-west1"

# Create bucket
gsutil mb -p ${PROJECT_ID} -l ${REGION} gs://${BUCKET_NAME}

# Verify
gsutil ls -p ${PROJECT_ID}
```

**Add to `.env`:**
```env
DATAFLOW_STAGING_BUCKET=gs://dataflow-staging-${PROJECT_ID}
DATAFLOW_TEMP_BUCKET=gs://dataflow-temp-${PROJECT_ID}
DATAFLOW_REGION=europe-west1
DATAFLOW_NETWORK=default
```

---

## STEP 3: Grant IAM Permissions to Service Account

Your service account needs Dataflow-specific roles.

```bash
export PROJECT_ID="your-project-id"
export SERVICE_ACCOUNT="ecommerce-pipeline@${PROJECT_ID}.iam.gserviceaccount.com"

# Add required roles
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/dataflow.worker"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/dataflow.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/compute.serviceAgent"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/storage.objectAdmin"

# Verify permissions
gcloud projects get-iam-policy ${PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${SERVICE_ACCOUNT}"
```

---

## STEP 4: Modify Pipeline for Dataflow Runner

### 4a. Update beam/pipeline.py

Replace the `StandardOptions` section to use DataflowRunner:

**Current code (lines ~130-150):**
```python
# OLD - DirectRunner (local execution)
options = PipelineOptions()
options.view_as(StandardOptions).runner = "DirectRunner"
```

**Replace with:**
```python
# NEW - DataflowRunner (GCP execution)
options = PipelineOptions(
    project=PROJECT_ID,
    region="europe-west1",
    runner="DataflowRunner",
    staging_location=f"gs://dataflow-staging-{PROJECT_ID}/staging",
    temp_location=f"gs://dataflow-staging-{PROJECT_ID}/temp",
    save_main_session=True,
    setup_file="./setup.py",  # Required for DataflowRunner
)
options.view_as(StandardOptions).runner = "DataflowRunner"
```

### 4b. Install Apache Beam with Dataflow support
```bash
pip install apache-beam[gcp]
```

### 4c. Create setup.py (required for DataflowRunner)
Create `setup.py` in project root:

```python
import setuptools

setuptools.setup(
    name='ecommerce-beam-pipeline',
    version='1.0.0',
    description='E-commerce ETL pipeline on Dataflow',
    packages=setuptools.find_packages(),
    install_requires=[
        'apache-beam[gcp]==2.53.0',
        'google-cloud-bigquery==3.17.0',
        'google-cloud-storage==2.14.0',
        'google-cloud-pubsub==2.19.0',
        'python-dotenv==1.0.0',
    ],
)
```

---

## STEP 5: Authentication Setup

### 5a. Set Service Account Credentials
```bash
export PROJECT_ID="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# Verify authentication
gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
gcloud config set project ${PROJECT_ID}
gcloud auth application-default login
```

### 5b. Update .env
```env
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
PROJECT_ID=your-project-id
DATAFLOW_STAGING_BUCKET=gs://dataflow-staging-${PROJECT_ID}
DATAFLOW_TEMP_BUCKET=gs://dataflow-staging-${PROJECT_ID}/temp
DATAFLOW_REGION=europe-west1
```

---

## STEP 6: Create ETL Pipeline Script for Dataflow

Create `beam/dataflow_pipeline.py`:

```python
"""
Apache Beam pipeline: ETL/ELT on Dataflow (Production-Ready)

Features:
- Reads from Cloud Storage (CSV) or Pub/Sub
- Transforms and validates data
- Writes to BigQuery
- Error handling and logging
- Runs on Google Cloud Dataflow

Usage:
    python beam/dataflow_pipeline.py \
      --project my-project \
      --region europe-west1 \
      --runner DataflowRunner \
      --staging_location gs://bucket/staging \
      --temp_location gs://bucket/temp
"""

import argparse
import logging
import json
from datetime import datetime
from typing import Dict, Any

import apache_beam as beam
from apache_beam.options.pipeline_options import (
    PipelineOptions,
    StandardOptions,
    WorkerOptions,
    SetupOptions,
)
from apache_beam.io import ReadFromText, WriteToBigQuery
from apache_beam.transforms import DoFn, ParDo, Map
from apache_beam.utils.timestamp import Timestamp
import pandas as pd
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = os.getenv("PROJECT_ID")
DATASET = os.getenv("DATASET", "ecommerce_analytics")


# ============================================================================
# BEAM TRANSFORMS (ETL LOGIC)
# ============================================================================

class ParseCSV(beam.DoFn):
    """Parse CSV line into dictionary."""
    
    def __init__(self, headers):
        self.headers = headers
    
    def process(self, line):
        try:
            values = line.split(",")
            if len(values) != len(self.headers):
                raise ValueError(f"Column count mismatch")
            record = dict(zip(self.headers, values))
            yield record
        except Exception as e:
            logger.warning(f"Parse error: {line[:100]}, Error: {e}")
            yield None


class ValidateRecord(beam.DoFn):
    """Validate data quality."""
    
    def process(self, element):
        if element is None:
            return
        
        required_fields = ["id", "client_id", "status"]
        required_present = all(field in element for field in required_fields)
        
        if not required_present:
            missing = [f for f in required_fields if f not in element]
            logger.warning(f"Missing fields: {missing}")
            yield beam.pvalue.TaggedOutput("invalid", {
                **element,
                "error": f"Missing: {missing}",
                "processed_at": datetime.now().isoformat(),
            })
        else:
            yield beam.pvalue.TaggedOutput("valid", element)


class EnrichRecord(beam.DoFn):
    """Add computed fields and metadata."""
    
    def process(self, element):
        try:
            # Add metadata
            element["processed_timestamp"] = datetime.now().isoformat()
            element["pipeline_version"] = "2.0"
            element["execution_environment"] = "dataflow"
            
            # Add computed fields (example)
            if "total_amount" in element and element["total_amount"]:
                try:
                    element["total_amount_numeric"] = float(element["total_amount"])
                    element["amount_category"] = "high" if float(element["total_amount"]) > 100 else "low"
                except:
                    element["total_amount_numeric"] = 0
                    element["amount_category"] = "unknown"
            
            yield element
        except Exception as e:
            logger.error(f"Enrichment error: {e}")
            yield element


class FilterRecords(beam.DoFn):
    """Filter by status."""
    
    def process(self, element, status_filter="completed"):
        if element.get("status") == status_filter:
            yield element


# ============================================================================
# PIPELINE DEFINITION
# ============================================================================

def run_pipeline(argv=None):
    """Main pipeline execution."""
    
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input',
        dest='input',
        default='gs://YOUR_BUCKET/data/orders.csv',
        help='Input GCS path'
    )
    parser.add_argument(
        '--output_table',
        dest='output_table',
        default=f'{PROJECT_ID}:{DATASET}.orders_processed',
        help='Output BigQuery table'
    )
    parser.add_argument(
        '--error_table',
        dest='error_table',
        default=f'{PROJECT_ID}:{DATASET}.orders_errors',
        help='Error BigQuery table'
    )
    
    known_args, pipeline_args = parser.parse_known_args(argv)
    
    # Pipeline options
    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(StandardOptions).runner = 'DataflowRunner'
    
    # Worker options
    pipeline_options.view_as(WorkerOptions).num_workers = 2
    pipeline_options.view_as(WorkerOptions).machine_type = 'n1-standard-2'
    
    # Setup options
    pipeline_options.view_as(SetupOptions).save_main_session = True
    
    # Create pipeline
    with beam.Pipeline(options=pipeline_options) as p:
        
        # Read from GCS
        lines = p | 'ReadCSV' >> ReadFromText(known_args.input)
        
        # Extract headers (first line)
        headers = lines | 'GetHeaders' >> beam.Filter(
            lambda line: line != known_args.input  # Skip input path
        ) | 'LimitToOne' >> beam.combiners.Top.Of(1)
        
        # Parse CSV
        records = lines | 'ParseCSV' >> ParDo(
            ParseCSV(['id', 'client_id', 'status', 'total_amount'])
        )
        
        # Validate
        valid, invalid = (
            records 
            | 'Validate' >> ParDo(ValidateRecord()).with_outputs(
                'valid', 'invalid', main='valid'
            )
        )
        
        # Enrich valid records
        enriched = (
            valid
            | 'Enrich' >> ParDo(EnrichRecord())
        )
        
        # Filter (optional)
        processed = (
            enriched
            | 'Filter' >> ParDo(FilterRecords("completed"))
        )
        
        # Write valid records to BigQuery
        (
            processed
            | 'WriteToBigQuery' >> WriteToBigQuery(
                table=known_args.output_table,
                create_disposition='CREATE_IF_NEEDED',
                write_disposition='WRITE_APPEND',
                method='STREAMING_INSERTS',
            )
        )
        
        # Write invalid records to error table
        (
            invalid
            | 'WriteErrors' >> WriteToBigQuery(
                table=known_args.error_table,
                create_disposition='CREATE_IF_NEEDED',
                write_disposition='WRITE_APPEND',
            )
        )


if __name__ == '__main__':
    logger.info("Starting Dataflow ETL Pipeline")
    run_pipeline()
```

---

## STEP 7: Create BigQuery Tables

```bash
# Set variables
export PROJECT_ID="your-project-id"
export DATASET="ecommerce_analytics"

# Create dataset
bq mk --project_id=${PROJECT_ID} --dataset_description="E-commerce analytics" ${DATASET}

# Create processed table
bq mk --table \
  ${PROJECT_ID}:${DATASET}.orders_processed \
  id:STRING,client_id:STRING,status:STRING,total_amount:FLOAT64,\
  processed_timestamp:TIMESTAMP,pipeline_version:STRING,execution_environment:STRING,\
  total_amount_numeric:FLOAT64,amount_category:STRING

# Create error table
bq mk --table \
  ${PROJECT_ID}:${DATASET}.orders_errors \
  error:STRING,processed_at:TIMESTAMP
```

---

## STEP 8: Deploy Pipeline to Dataflow

### 8a. Upload data to GCS
```bash
export BUCKET="gs://your-bucket"
gsutil cp data/raw/orders.csv ${BUCKET}/data/orders.csv
```

### 8b. Submit job to Dataflow
```bash
export PROJECT_ID="your-project-id"
export REGION="europe-west1"
export BUCKET="gs://your-bucket"

python beam/dataflow_pipeline.py \
  --project=${PROJECT_ID} \
  --region=${REGION} \
  --runner=DataflowRunner \
  --staging_location=${BUCKET}/staging \
  --temp_location=${BUCKET}/temp \
  --input=${BUCKET}/data/orders.csv \
  --output_table=${PROJECT_ID}:ecommerce_analytics.orders_processed \
  --error_table=${PROJECT_ID}:ecommerce_analytics.orders_errors
```

### 8c. Create shell script for easy execution
Create `beam/submit_to_dataflow.sh`:

```bash
#!/bin/bash

# ============================================================================
# SUBMIT APACHE BEAM PIPELINE TO DATAFLOW
# ============================================================================

set -e

# Load environment
source .env

echo "[INFO] Submitting pipeline to Dataflow..."
echo "[INFO] Project: ${PROJECT_ID}"
echo "[INFO] Region: ${DATAFLOW_REGION}"
echo ""

python beam/dataflow_pipeline.py \
  --project=${PROJECT_ID} \
  --region=${DATAFLOW_REGION} \
  --runner=DataflowRunner \
  --staging_location=${DATAFLOW_STAGING_BUCKET}/staging \
  --temp_location=${DATAFLOW_TEMP_BUCKET} \
  --input=gs://${BUCKET}/data/orders.csv \
  --output_table=${PROJECT_ID}:${DATASET}.orders_processed \
  --error_table=${PROJECT_ID}:${DATASET}.orders_errors \
  --num_workers=2 \
  --machine_type=n1-standard-2

echo ""
echo "[✓] Pipeline submitted to Dataflow"
echo "[INFO] Check status: https://console.cloud.google.com/dataflow/jobs?project=${PROJECT_ID}"
```

---

## STEP 9: Monitor Pipeline Execution

### 9a. View job list in Cloud Console
```bash
gcloud dataflow jobs list --project=${PROJECT_ID} --region=${DATAFLOW_REGION}
```

### 9b. Get specific job details
```bash
gcloud dataflow jobs list \
  --project=${PROJECT_ID} \
  --region=${DATAFLOW_REGION} \
  --format="table(name,state)"
```

### 9c. View logs
```bash
export JOB_ID="dataflow-job-id"

gcloud logging read \
  "resource.type=dataflow_step AND labels.job_id=${JOB_ID}" \
  --limit=50 \
  --format=json \
  --project=${PROJECT_ID}
```

### 9d. Monitor in Cloud Console (Best Option)
```
https://console.cloud.google.com/dataflow/jobs?project=YOUR_PROJECT_ID
```

---

## STEP 10: Automate with Cloud Scheduler

### 10a. Create scheduler job
```bash
export PROJECT_ID="your-project-id"
export REGION="europe-west1"

# Create Cloud Function that triggers the pipeline
gcloud functions deploy trigger-dataflow-pipeline \
  --runtime python311 \
  --trigger-topic dataflow-trigger \
  --entry-point trigger_pipeline \
  --project=${PROJECT_ID} \
  --region=${REGION}
```

### 10b. Create scheduler
```bash
gcloud scheduler jobs create pubsub trigger-dataflow-daily \
  --schedule="0 2 * * *" \
  --topic=dataflow-trigger \
  --message-body='{"project":"'${PROJECT_ID}'"}' \
  --project=${PROJECT_ID} \
  --location=${REGION}
```

---

## STEP 11: Cost Optimization

### 11a. Use Autoscaling
```bash
# In pipeline options:
pipeline_options.view_as(WorkerOptions).autoscaling_algorithm = 'THROUGHPUT_BASED'
pipeline_options.view_as(WorkerOptions).max_num_workers = 10
pipeline_options.view_as(WorkerOptions).num_workers = 2
```

### 11b. Use Spot VMs (80% cheaper)
```bash
gcloud dataflow jobs create my-job \
  --use-public-ips \
  --machine-type=n1-standard-2 \
  --worker-region=${REGION} \
  --enable-streaming-engine
```

### 11c. Monitor costs
```bash
bq query --use_legacy_sql=false "
SELECT 
  DATE(creation_time) as date,
  SUM(total_bytes_billed)/POW(10,12) as cost_usd
FROM \`${PROJECT_ID}.region-us.\`INFORMATION_SCHEMA.JOBS_BY_PROJECT\`
WHERE DATE(creation_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY date
ORDER BY date DESC
"
```

---

## Troubleshooting

### Issue: "Dataflow API not enabled"
```bash
gcloud services enable dataflow.googleapis.com
```

### Issue: "Permission denied" errors
```bash
gcloud projects get-iam-policy ${PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:*"
```

### Issue: "Staging bucket not found"
```bash
gsutil ls
gsutil mb gs://dataflow-staging-${PROJECT_ID}
```

### Issue: "Python version mismatch"
```bash
python --version  # Must be 3.11+
pip install --upgrade apache-beam[gcp]
```

---

## Quick Reference Commands

| Task | Command |
|------|---------|
| Check API status | `gcloud services list --enabled` |
| List Dataflow jobs | `gcloud dataflow jobs list --region=REGION` |
| Submit pipeline | `bash beam/submit_to_dataflow.sh` |
| View job logs | `gcloud logging read "resource.type=dataflow_step"` |
| Cancel job | `gcloud dataflow jobs cancel JOB_ID --region=REGION` |
| Query results | `bq query "SELECT * FROM PROJECT:DATASET.TABLE LIMIT 10"` |

---

## Summary

✅ Enable APIs (Dataflow, Compute, BQ, Storage)  
✅ Create staging bucket  
✅ Grant IAM permissions  
✅ Update pipeline for DataflowRunner  
✅ Create BigQuery tables  
✅ Submit job to Dataflow  
✅ Monitor execution  
✅ (Optional) Automate with Cloud Scheduler  

**Result:** Your ETL pipeline runs on managed Dataflow infrastructure at scale!

