#!/bin/bash

# ============================================================================
# DATAFLOW ETL PIPELINE DEPLOYMENT SCRIPT
# ============================================================================
#
# This script submits the Apache Beam pipeline to Google Cloud Dataflow
# for production ETL/ELT processing.
#
# Prerequisites:
#   - Google Cloud Project with Dataflow API enabled
#   - Service account with Dataflow admin permissions
#   - Python 3.11+ with apache-beam[gcp] installed
#   - .env file configured with GCP settings
#
# Usage:
#   bash beam/submit_to_dataflow.sh                    # Uses defaults
#   bash beam/submit_to_dataflow.sh --input gs://bucket/data.csv
#   bash beam/submit_to_dataflow.sh --dry-run           # Preview only
#
# ============================================================================

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Load environment
if [ ! -f .env ]; then
    log_error ".env file not found. Please create it from .env.example"
    exit 1
fi

source .env

# Default values
INPUT="${INPUT_DATA:-gs://your-bucket/data/orders.csv}"
OUTPUT_TABLE="${OUTPUT_TABLE:-${PROJECT_ID}:${DATASET}.orders_processed}"
ERROR_TABLE="${ERROR_TABLE:-${PROJECT_ID}:${DATASET}.orders_errors}"
DRY_RUN=false
WORKER_MACHINE_TYPE="${WORKER_MACHINE_TYPE:-n1-standard-2}"
NUM_WORKERS="${NUM_WORKERS:-2}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --input)
            INPUT="$2"
            shift 2
            ;;
        --output-table)
            OUTPUT_TABLE="$2"
            shift 2
            ;;
        --error-table)
            ERROR_TABLE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --workers)
            NUM_WORKERS="$2"
            shift 2
            ;;
        --machine-type)
            WORKER_MACHINE_TYPE="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate environment
log_info "Validating environment..."

if [ -z "$PROJECT_ID" ]; then
    log_error "PROJECT_ID not set in .env"
    exit 1
fi

if [ -z "$DATAFLOW_REGION" ]; then
    log_error "DATAFLOW_REGION not set in .env"
    exit 1
fi

if [ -z "$DATAFLOW_STAGING_BUCKET" ]; then
    log_error "DATAFLOW_STAGING_BUCKET not set in .env"
    exit 1
fi

# Verify GCP access
log_info "Verifying GCP authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    log_error "Not authenticated with gcloud. Run: gcloud auth login"
    exit 1
fi

log_success "Authenticated with GCP"

# Verify APIs are enabled
log_info "Checking required APIs..."
for api in dataflow.googleapis.com compute.googleapis.com bigquery.googleapis.com storage-api.googleapis.com; do
    if ! gcloud services list --enabled --project=${PROJECT_ID} | grep -q $api; then
        log_warning "API not enabled: $api"
        log_info "Run: gcloud services enable $api --project=${PROJECT_ID}"
    fi
done

# Display configuration
echo ""
log_info "Pipeline Configuration:"
echo "  ${BLUE}Project ID:${NC}           ${PROJECT_ID}"
echo "  ${BLUE}Region:${NC}               ${DATAFLOW_REGION}"
echo "  ${BLUE}Input:${NC}                ${INPUT}"
echo "  ${BLUE}Output Table:${NC}         ${OUTPUT_TABLE}"
echo "  ${BLUE}Error Table:${NC}          ${ERROR_TABLE}"
echo "  ${BLUE}Staging Bucket:${NC}       ${DATAFLOW_STAGING_BUCKET}"
echo "  ${BLUE}Temp Bucket:${NC}          ${DATAFLOW_TEMP_BUCKET}"
echo "  ${BLUE}Workers:${NC}              ${NUM_WORKERS}"
echo "  ${BLUE}Machine Type:${NC}         ${WORKER_MACHINE_TYPE}"
echo ""

# Verify input file exists
log_info "Verifying input file..."
if ! gsutil ls "${INPUT}" > /dev/null 2>&1; then
    log_error "Input file not found: ${INPUT}"
    log_info "Upload data to GCS first: gsutil cp data/raw/orders.csv ${INPUT}"
    exit 1
fi
log_success "Input file found"

# Check Python environment
log_info "Checking Python environment..."
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
log_info "Python version: ${PYTHON_VERSION}"

if ! python -c "import apache_beam" 2>/dev/null; then
    log_error "apache-beam not installed. Run: pip install apache-beam[gcp]"
    exit 1
fi
log_success "Apache Beam installed"

# DRY RUN?
if [ "$DRY_RUN" = true ]; then
    log_warning "DRY RUN MODE - Not submitting to Dataflow"
    log_info "To submit, run without --dry-run flag"
    exit 0
fi

# Confirm before submitting
echo ""
read -p "$(echo -e ${YELLOW})Submit this pipeline to Dataflow? (yes/no)${NC} " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warning "Cancelled"
    exit 0
fi

# Submit pipeline
echo ""
log_info "=" * 70
log_info "Submitting pipeline to Dataflow..."
log_info "=" * 70
echo ""

python beam/dataflow_etl_pipeline.py \
  --project=${PROJECT_ID} \
  --region=${DATAFLOW_REGION} \
  --runner=DataflowRunner \
  --staging_location=${DATAFLOW_STAGING_BUCKET}/staging \
  --temp_location=${DATAFLOW_TEMP_BUCKET} \
  --num_workers=${NUM_WORKERS} \
  --machine_type=${WORKER_MACHINE_TYPE} \
  --save_main_session \
  --input="${INPUT}" \
  --output_table="${OUTPUT_TABLE}" \
  --error_table="${ERROR_TABLE}"

# Get job ID from output
JOB_ID=$(gcloud dataflow jobs list \
  --project=${PROJECT_ID} \
  --region=${DATAFLOW_REGION} \
  --format="value(name)" \
  --limit=1 \
  --filter="state:RUNNING OR state:PENDING")

echo ""
echo "=" * 70
log_success "Pipeline submitted to Dataflow!"
log_success "Job ID: ${JOB_ID}"
echo "=" * 70
echo ""

# Provide monitoring links
log_info "Monitor your pipeline:"
echo "  Cloud Console: https://console.cloud.google.com/dataflow/jobs/${JOB_ID}?project=${PROJECT_ID}"
echo "  Command line:  gcloud dataflow jobs describe ${JOB_ID} --region=${DATAFLOW_REGION} --project=${PROJECT_ID}"
echo ""

log_info "View logs:"
echo "  gcloud logging read \"resource.type=dataflow_step AND labels.job_id=${JOB_ID}\" --limit=50 --project=${PROJECT_ID}"
echo ""

log_info "Cancel job (if needed):"
echo "  gcloud dataflow jobs cancel ${JOB_ID} --region=${DATAFLOW_REGION} --project=${PROJECT_ID}"
echo ""

# Poll for completion
log_info "Waiting for pipeline to start..."
max_wait=60
waited=0

while [ $waited -lt $max_wait ]; do
    STATE=$(gcloud dataflow jobs describe ${JOB_ID} \
      --project=${PROJECT_ID} \
      --region=${DATAFLOW_REGION} \
      --format="value(state)")
    
    if [ "$STATE" = "RUNNING" ]; then
        log_success "Pipeline is now running!"
        break
    elif [ "$STATE" = "DONE" ]; then
        log_success "Pipeline completed!"
        break
    elif [ "$STATE" = "FAILED" ]; then
        log_error "Pipeline failed!"
        exit 1
    fi
    
    echo -n "."
    sleep 5
    ((waited+=5))
done

echo ""
echo "=" * 70
log_success "Dataflow pipeline deployment complete!"
echo "=" * 70
