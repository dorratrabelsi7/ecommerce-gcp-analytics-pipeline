#!/bin/bash

# ============================================================================
# CLOUD FUNCTION DEPLOYMENT SCRIPT
# E-Commerce Analytics Pipeline
# ============================================================================
#
# Deploys a GCS-triggered Cloud Function (gen2) that processes uploaded files
# and writes to BigQuery with error handling via dead-letter queue.
#
# COST NOTE: Cloud Functions gen2 free tier = 2M invocations/month.
# This function is triggered only on file upload, not on a schedule.
# Expected invocations: < 100/month → always free.
#
# Usage: bash deploy/deploy_function.sh

set -euo pipefail

# Load configuration
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

PROJECT_ID="${PROJECT_ID:-ecommerce-494010}"
REGION="${REGION:-europe-west1}"
DATASET="${DATASET:-ecommerce_analytics}"
BUCKET="${BUCKET:-ecommerce-raw-${PROJECT_ID}}"
FUNCTION_NAME="process-gcs-upload"
RUNTIME="python311"

echo "[INFO] Deploying Cloud Function: $FUNCTION_NAME"

# Check if functions directory exists
if [ ! -d "functions/process_upload" ]; then
    echo "[ERROR] functions/process_upload directory not found"
    exit 1
fi

# Deploy the function
gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=$RUNTIME \
    --region=$REGION \
    --source=functions/process_upload \
    --entry-point=process_upload \
    --trigger-resource=$BUCKET \
    --trigger-event="google.cloud.storage.object.v1.finalized" \
    --memory=256MB \
    --timeout=120s \
    --max-instances=3 \
    --set-env-vars="PROJECT_ID=$PROJECT_ID,DATASET=$DATASET" \
    --project=$PROJECT_ID

echo "[✓] Cloud Function deployed successfully"
echo "    Function: $FUNCTION_NAME"
echo "    URL: https://console.cloud.google.com/functions/details/$REGION/$FUNCTION_NAME?project=$PROJECT_ID"
