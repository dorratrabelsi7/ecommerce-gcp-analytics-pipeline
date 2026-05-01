#!/bin/bash

# ============================================================================
# DATAFLOW ACTIVATION - FULL SETUP
# Project: ecommerce-494010
# ============================================================================
#
# Ce script active Dataflow et l'intègre avec Cloud Scheduler
#
# Prérequis:
#   1. Fichier credentials JSON (service account key)
#   2. gcloud CLI installé et authentifié
#   3. Ce script dans le répertoire racine du projet
#
# Usage:
#   bash activate_dataflow.sh /path/to/service-account-key.json

set -e

# Configuration
PROJECT_ID="ecommerce-494010"
PROJECT_NUMBER="751054966924"
REGION="europe-west1"
DATASET="ecommerce_analytics"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

# Verify credentials file
if [ -z "$1" ]; then
    log_error "Credentials JSON file required!"
    echo "Usage: bash activate_dataflow.sh /path/to/service-account-key.json"
    exit 1
fi

CREDENTIALS_FILE="$1"

if [ ! -f "$CREDENTIALS_FILE" ]; then
    log_error "Credentials file not found: $CREDENTIALS_FILE"
    exit 1
fi

log_success "Credentials file found: $CREDENTIALS_FILE"

# ============================================================================
# STEP 1: AUTHENTICATE
# ============================================================================

echo ""
log_info "===== STEP 1: Authenticate with GCP ====="

export GOOGLE_APPLICATION_CREDENTIALS="$CREDENTIALS_FILE"

gcloud auth activate-service-account --key-file=$CREDENTIALS_FILE
gcloud config set project $PROJECT_ID

log_success "Authenticated with project: $PROJECT_ID"

# ============================================================================
# STEP 2: ENABLE APIs
# ============================================================================

echo ""
log_info "===== STEP 2: Enable Required APIs ====="

apis=(
    "dataflow.googleapis.com"
    "compute.googleapis.com"
    "bigquery.googleapis.com"
    "storage-api.googleapis.com"
    "cloudscheduler.googleapis.com"
    "pubsub.googleapis.com"
)

for api in "${apis[@]}"; do
    log_info "Enabling $api..."
    gcloud services enable $api --project=$PROJECT_ID --quiet
done

log_success "All APIs enabled"

# ============================================================================
# STEP 3: CREATE STORAGE BUCKETS
# ============================================================================

echo ""
log_info "===== STEP 3: Create GCS Buckets ====="

STAGING_BUCKET="gs://dataflow-staging-${PROJECT_ID}"
TEMP_BUCKET="gs://dataflow-temp-${PROJECT_ID}"
DATA_BUCKET="gs://data-${PROJECT_ID}"

for bucket in $STAGING_BUCKET $TEMP_BUCKET $DATA_BUCKET; do
    BUCKET_NAME=$(echo $bucket | sed 's/gs:\/\///')
    
    if gsutil ls -b $bucket > /dev/null 2>&1; then
        log_warn "Bucket already exists: $bucket"
    else
        log_info "Creating bucket: $bucket"
        gsutil mb -p $PROJECT_ID -l $REGION $bucket
    fi
done

log_success "All buckets ready"

# ============================================================================
# STEP 4: CREATE BigQuery DATASET & TABLES
# ============================================================================

echo ""
log_info "===== STEP 4: Setup BigQuery ====="

# Create dataset
log_info "Creating BigQuery dataset: $DATASET"
bq mk --project_id=$PROJECT_ID \
    --dataset_description="E-commerce analytics pipeline" \
    --location=$REGION \
    $DATASET 2>/dev/null || log_warn "Dataset may already exist"

# Create output tables
log_info "Creating BigQuery tables..."

bq mk --table \
    --project_id=$PROJECT_ID \
    --schema="id:STRING,client_id:STRING,status:STRING,total_amount:FLOAT64,processed_timestamp:TIMESTAMP,pipeline_version:STRING,execution_environment:STRING,total_amount_numeric:FLOAT64,amount_category:STRING" \
    ${DATASET}.orders_processed 2>/dev/null || log_warn "Table orders_processed may already exist"

bq mk --table \
    --project_id=$PROJECT_ID \
    ${DATASET}.orders_errors 2>/dev/null || log_warn "Table orders_errors may already exist"

log_success "BigQuery setup complete"

# ============================================================================
# STEP 5: GRANT PERMISSIONS
# ============================================================================

echo ""
log_info "===== STEP 5: Grant Permissions ====="

# Extract service account email from credentials
SERVICE_ACCOUNT=$(grep -o '"client_email": "[^"]*' $CREDENTIALS_FILE | cut -d'"' -f4)
log_info "Service Account: $SERVICE_ACCOUNT"

roles=(
    "roles/dataflow.admin"
    "roles/dataflow.worker"
    "roles/bigquery.dataEditor"
    "roles/storage.objectAdmin"
    "roles/compute.serviceAgent"
)

for role in "${roles[@]}"; do
    log_info "Granting role: $role"
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="$role" \
        --quiet 2>/dev/null || log_warn "Role grant may have failed"
done

log_success "Permissions configured"

# ============================================================================
# STEP 6: UPLOAD SAMPLE DATA
# ============================================================================

echo ""
log_info "===== STEP 6: Upload Sample Data ====="

if [ -f "data/raw/orders.csv" ]; then
    log_info "Uploading data/raw/orders.csv to GCS..."
    gsutil cp data/raw/orders.csv ${DATA_BUCKET}/orders.csv
    log_success "Data uploaded"
else
    log_warn "data/raw/orders.csv not found - skipping upload"
fi

# ============================================================================
# STEP 7: UPDATE .env FILE
# ============================================================================

echo ""
log_info "===== STEP 7: Update .env File ====="

if [ ! -f ".env" ]; then
    log_error ".env file not found!"
    log_info "Creating .env with Dataflow configuration..."
    cat > .env << EOF
# GCP Configuration
PROJECT_ID=$PROJECT_ID
PROJECT_NUMBER=$PROJECT_NUMBER
REGION=$REGION
DATASET=$DATASET

# Dataflow Configuration
DATAFLOW_STAGING_BUCKET=$STAGING_BUCKET
DATAFLOW_TEMP_BUCKET=$TEMP_BUCKET
DATAFLOW_REGION=$REGION

# Storage
DATA_BUCKET=$DATA_BUCKET
BUCKET=dataflow-staging-${PROJECT_ID}

# Authentication
GOOGLE_APPLICATION_CREDENTIALS=$CREDENTIALS_FILE

# Pub/Sub (Optional - for streaming)
PUBSUB_TOPIC=orders-realtime
PUBSUB_SUB=orders-realtime-sub
EOF
    log_success ".env file created"
else
    log_warn ".env already exists - not overwriting"
    log_info "Update manually with:"
    echo "  PROJECT_ID=$PROJECT_ID"
    echo "  DATAFLOW_STAGING_BUCKET=$STAGING_BUCKET"
    echo "  DATAFLOW_TEMP_BUCKET=$TEMP_BUCKET"
    echo "  GOOGLE_APPLICATION_CREDENTIALS=$CREDENTIALS_FILE"
fi

# ============================================================================
# STEP 8: VERIFY SETUP
# ============================================================================

echo ""
log_info "===== STEP 8: Verify Setup ====="

log_info "Verifying BigQuery..."
bq ls --project_id=$PROJECT_ID

log_info "Verifying GCS buckets..."
gsutil ls -p $PROJECT_ID | grep dataflow

log_info "Verifying service account..."
gcloud iam service-accounts list --project=$PROJECT_ID

# ============================================================================
# FINAL: SUMMARY
# ============================================================================

echo ""
echo "========================================================================"
log_success "DATAFLOW ACTIVATION COMPLETE!"
echo "========================================================================"
echo ""
echo "✅ Completed:"
echo "   • APIs enabled (Dataflow, Compute, BigQuery, Storage)"
echo "   • GCS buckets created (staging, temp, data)"
echo "   • BigQuery dataset & tables created"
echo "   • Service account permissions granted"
echo "   • .env file configured"
echo ""
echo "📝 Next Steps:"
echo "   1. Install Apache Beam: pip install apache-beam[gcp]"
echo "   2. Generate test data: python scripts/generate_data.py"
echo "   3. Submit pipeline: bash beam/submit_to_dataflow.sh"
echo ""
echo "📊 Project Details:"
echo "   Project ID: $PROJECT_ID"
echo "   Region: $REGION"
echo "   Dataset: $DATASET"
echo "   Staging: $STAGING_BUCKET"
echo ""
echo "🔗 Cloud Console:"
echo "   https://console.cloud.google.com/dataflow/jobs?project=$PROJECT_ID"
echo ""
echo "========================================================================"
