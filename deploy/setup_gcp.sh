#!/bin/bash

# ============================================================================
# GCP INFRASTRUCTURE SETUP SCRIPT
# E-Commerce Analytics Pipeline - $0 Free Tier
# ============================================================================
#
# This script sets up all necessary GCP resources within the free tier:
# - Cloud Storage buckets
# - Pub/Sub topics and subscriptions
# - BigQuery dataset
# - Cloud Logging
#
# COST NOTE: All resources created are within GCP Free Tier limits.
# Never enable Dataflow, Compute Engine, or Cloud Run — they incur costs.
#
# Usage:
#   bash deploy/setup_gcp.sh --dry-run    # Preview commands without executing
#   bash deploy/setup_gcp.sh               # Execute setup

set -euo pipefail

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load from .env if it exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

PROJECT_ID="${PROJECT_ID:-ecommerce-494010}"
REGION="${REGION:-europe-west1}"
DATASET="${DATASET:-ecommerce_analytics}"
BUCKET="${BUCKET:-ecommerce-raw-${PROJECT_ID}}"
PUBSUB_TOPIC="${PUBSUB_TOPIC:-orders-realtime}"
PUBSUB_TOPIC_DLQ="${PUBSUB_TOPIC_DLQ:-orders-realtime-dlq}"
PUBSUB_SUB="${PUBSUB_SUB:-orders-sub}"

# Parse arguments
DRY_RUN=0
if [[ "$@" == *"--dry-run"* ]]; then
    DRY_RUN=1
fi

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

run_command() {
    local cmd="$1"
    if [ $DRY_RUN -eq 1 ]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} $cmd"
    else
        log_info "Executing: $cmd"
        eval "$cmd" || {
            log_error "Command failed: $cmd"
            return 1
        }
    fi
}

# ============================================================================
# STEP 1: VERIFY AUTHENTICATION
# ============================================================================

log_info "Verifying GCP authentication..."

if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    log_error "Not authenticated with gcloud. Run: gcloud auth login"
    exit 1
fi

log_success "GCP authentication verified"

# ============================================================================
# STEP 2: SET ACTIVE PROJECT
# ============================================================================

log_info "Setting active project to: $PROJECT_ID"
run_command "gcloud config set project $PROJECT_ID"
log_success "Project set to $PROJECT_ID"

# ============================================================================
# STEP 3: ENABLE REQUIRED APIs (FREE TIER ONLY)
# ============================================================================

log_info "Enabling required APIs (free tier services only)..."

APIs=(
    "storage.googleapis.com"
    "bigquery.googleapis.com"
    "pubsub.googleapis.com"
    "cloudfunctions.googleapis.com"
    "cloudscheduler.googleapis.com"
    "logging.googleapis.com"
    "monitoring.googleapis.com"
)

for api in "${APIs[@]}"; do
    run_command "gcloud services enable $api --project=$PROJECT_ID"
done

log_success "All required APIs enabled"

# ============================================================================
# STEP 4: CREATE GCS BUCKET
# ============================================================================

log_info "Creating Cloud Storage bucket: gs://$BUCKET"

run_command "gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET" || {
    log_warning "Bucket may already exist or creation failed"
}

run_command "gsutil versioning set on gs://$BUCKET"
log_success "GCS bucket configured"

# ============================================================================
# STEP 5: CREATE GCS DIRECTORY STRUCTURE
# ============================================================================

log_info "Creating GCS directory structure..."

# Create subdirectories via placeholder files (GCS doesn't have real dirs)
run_command "echo 'placeholder' | gsutil cp - gs://$BUCKET/raw/clients/.placeholder"
run_command "echo 'placeholder' | gsutil cp - gs://$BUCKET/raw/orders/.placeholder"
run_command "echo 'placeholder' | gsutil cp - gs://$BUCKET/raw/incidents/.placeholder"
run_command "echo 'placeholder' | gsutil cp - gs://$BUCKET/raw/page_views/.placeholder"

log_success "GCS directory structure created"

# ============================================================================
# STEP 6: CREATE PUB/SUB TOPIC & SUBSCRIPTION
# ============================================================================

log_info "Creating Pub/Sub topic: $PUBSUB_TOPIC"

run_command "gcloud pubsub topics create $PUBSUB_TOPIC --project=$PROJECT_ID" || {
    log_warning "Topic may already exist"
}

log_info "Creating Pub/Sub subscription: $PUBSUB_SUB"

run_command "gcloud pubsub subscriptions create $PUBSUB_SUB \
    --topic=$PUBSUB_TOPIC \
    --ack-deadline=60 \
    --message-retention-duration=10m \
    --project=$PROJECT_ID" || {
    log_warning "Subscription may already exist"
}

log_success "Pub/Sub topic and subscription created"

# ============================================================================
# STEP 7: CREATE DEAD-LETTER QUEUE TOPIC
# ============================================================================

log_info "Creating dead-letter queue topic: $PUBSUB_TOPIC_DLQ"

run_command "gcloud pubsub topics create $PUBSUB_TOPIC_DLQ --project=$PROJECT_ID" || {
    log_warning "DLQ topic may already exist"
}

log_success "Dead-letter queue created"

# ============================================================================
# STEP 8: CREATE BIGQUERY DATASET
# ============================================================================

log_info "Creating BigQuery dataset: $DATASET"

run_command "bq mk --dataset \
    --location=$REGION \
    --description='E-commerce analytics pipeline dataset' \
    --project_id=$PROJECT_ID \
    $DATASET" || {
    log_warning "Dataset may already exist"
}

log_success "BigQuery dataset created"

# ============================================================================
# STEP 9: UPLOAD CLEANED DATA TO GCS
# ============================================================================

if [ -d "data/clean" ]; then
    log_info "Uploading cleaned data files to GCS..."
    
    for file in data/clean/*_clean.csv; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            run_command "gsutil cp $file gs://$BUCKET/raw/$filename"
        fi
    done
    
    log_success "Data files uploaded"
else
    log_warning "data/clean directory not found (run scripts/prepare_data.py first)"
fi

# ============================================================================
# STEP 10: PRINT RESOURCE SUMMARY
# ============================================================================

echo ""
echo -e "${BLUE}================================ RESOURCE SUMMARY ================================${NC}"
echo ""
echo -e "${GREEN}Cloud Storage:${NC}"
echo "  Bucket: https://console.cloud.google.com/storage/browser/$BUCKET?project=$PROJECT_ID"
echo ""
echo -e "${GREEN}Pub/Sub:${NC}"
echo "  Topic: $PUBSUB_TOPIC"
echo "    https://console.cloud.google.com/cloudpubsub/topic/detail/$PUBSUB_TOPIC?project=$PROJECT_ID"
echo "  Subscription: $PUBSUB_SUB"
echo "    https://console.cloud.google.com/cloudpubsub/subscription/detail/$PUBSUB_SUB?project=$PROJECT_ID"
echo "  DLQ: $PUBSUB_TOPIC_DLQ"
echo "    https://console.cloud.google.com/cloudpubsub/topic/detail/$PUBSUB_TOPIC_DLQ?project=$PROJECT_ID"
echo ""
echo -e "${GREEN}BigQuery:${NC}"
echo "  Dataset: $DATASET"
echo "    https://console.cloud.google.com/bigquery?project=$PROJECT_ID&p=$PROJECT_ID&d=$DATASET"
echo ""
echo -e "${BLUE}=================================================================================${NC}"

# ============================================================================
# STEP 11: PRINT COST REMINDER
# ============================================================================

echo ""
echo -e "${YELLOW}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║                        COST REMINDER                           ║${NC}"
echo -e "${YELLOW}║                                                                ║${NC}"
echo -e "${YELLOW}║ All resources created are within GCP Free Tier limits.         ║${NC}"
echo -e "${YELLOW}║                                                                ║${NC}"
echo -e "${YELLOW}║ ✓ Cloud Storage: 5 GB/month (using ~20 MB)                    ║${NC}"
echo -e "${YELLOW}║ ✓ BigQuery storage: 10 GB/month (using ~50 MB)                ║${NC}"
echo -e "${YELLOW}║ ✓ BigQuery queries: 1 TB/month (using ~100 MB)                ║${NC}"
echo -e "${YELLOW}║ ✓ Pub/Sub: 10 GB/month (using ~50 KB)                         ║${NC}"
echo -e "${YELLOW}║ ✓ Cloud Functions: 2M invocations/month (< 100)               ║${NC}"
echo -e "${YELLOW}║ ✓ Cloud Scheduler: 3 jobs/month                               ║${NC}"
echo -e "${YELLOW}║                                                                ║${NC}"
echo -e "${YELLOW}║ ❌ NEVER enable these services (not free):                    ║${NC}"
echo -e "${YELLOW}║    - Dataflow (use DirectRunner only)                         ║${NC}"
echo -e "${YELLOW}║    - Compute Engine                                           ║${NC}"
echo -e "${YELLOW}║    - Cloud Run                                                ║${NC}"
echo -e "${YELLOW}║    - Cloud SQL                                                ║${NC}"
echo -e "${YELLOW}║                                                                ║${NC}"
echo -e "${YELLOW}║ Monitor billing: https://console.cloud.google.com/billing    ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ $DRY_RUN -eq 1 ]; then
    log_warning "DRY-RUN mode: No actual changes were made"
    log_info "Run without --dry-run to create resources: bash deploy/setup_gcp.sh"
else
    log_success "GCP infrastructure setup complete!"
fi

exit 0
