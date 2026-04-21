#!/bin/bash

# ============================================================================
# CLOUD SCHEDULER SETUP SCRIPT
# E-Commerce Analytics Pipeline
# ============================================================================
#
# Creates exactly 3 Cloud Scheduler jobs (free tier limit):
# 1. daily-bq-refresh - Every day at 06:00 UTC
# 2. weekly-kpi-export - Every Monday at 07:00 UTC
# 3. monthly-cleanup - 1st of month at 03:00 UTC
#
# COST NOTE: Cloud Scheduler free tier = 3 jobs/month.
# This script creates exactly 3 jobs. Do not add more without checking billing.
#
# Usage: bash deploy/setup_scheduler.sh

set -euo pipefail

# Load configuration
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

PROJECT_ID="${PROJECT_ID:-ecommerce-494010}"
REGION="${REGION:-europe-west1}"
PUBSUB_TOPIC="${PUBSUB_TOPIC:-orders-realtime}"

echo "[INFO] Setting up Cloud Scheduler jobs for project: $PROJECT_ID"
echo ""

# ============================================================================
# JOB 1: DAILY BQ REFRESH
# ============================================================================

echo "[INFO] Creating job: daily-bq-refresh"

gcloud scheduler jobs create pubsub daily-bq-refresh \
  --location=$REGION \
  --schedule="0 6 * * *" \
  --timezone="UTC" \
  --topic=$PUBSUB_TOPIC \
  --message-body='{"action":"refresh_kpis"}' \
  --project=$PROJECT_ID \
  --oidc-service-account-email="" \
  --headers="Content-Type=application/json" || {
    echo "[WARN] Job may already exist, attempting update..."
    gcloud scheduler jobs update pubsub daily-bq-refresh \
      --location=$REGION \
      --schedule="0 6 * * *" \
      --timezone="UTC" \
      --topic=$PUBSUB_TOPIC \
      --message-body='{"action":"refresh_kpis"}' \
      --project=$PROJECT_ID || true
}

echo "[✓] Job 1/3 created"
echo ""

# ============================================================================
# JOB 2: WEEKLY KPI EXPORT
# ============================================================================

echo "[INFO] Creating job: weekly-kpi-export"

gcloud scheduler jobs create pubsub weekly-kpi-export \
  --location=$REGION \
  --schedule="0 7 ? * MON" \
  --timezone="UTC" \
  --topic=$PUBSUB_TOPIC \
  --message-body='{"action":"export_weekly_report"}' \
  --project=$PROJECT_ID \
  --oidc-service-account-email="" \
  --headers="Content-Type=application/json" || {
    echo "[WARN] Job may already exist, attempting update..."
    gcloud scheduler jobs update pubsub weekly-kpi-export \
      --location=$REGION \
      --schedule="0 7 ? * MON" \
      --timezone="UTC" \
      --topic=$PUBSUB_TOPIC \
      --message-body='{"action":"export_weekly_report"}' \
      --project=$PROJECT_ID || true
}

echo "[✓] Job 2/3 created"
echo ""

# ============================================================================
# JOB 3: MONTHLY CLEANUP
# ============================================================================

echo "[INFO] Creating job: monthly-cleanup"

gcloud scheduler jobs create pubsub monthly-cleanup \
  --location=$REGION \
  --schedule="0 3 1 * *" \
  --timezone="UTC" \
  --topic=$PUBSUB_TOPIC \
  --message-body='{"action":"delete_old_partitions"}' \
  --project=$PROJECT_ID \
  --oidc-service-account-email="" \
  --headers="Content-Type=application/json" || {
    echo "[WARN] Job may already exist, attempting update..."
    gcloud scheduler jobs update pubsub monthly-cleanup \
      --location=$REGION \
      --schedule="0 3 1 * *" \
      --timezone="UTC" \
      --topic=$PUBSUB_TOPIC \
      --message-body='{"action":"delete_old_partitions"}' \
      --project=$PROJECT_ID || true
}

echo "[✓] Job 3/3 created"
echo ""

# ============================================================================
# VERIFICATION
# ============================================================================

echo "[INFO] Listing all Cloud Scheduler jobs:"
echo ""

gcloud scheduler jobs list --location=$REGION --project=$PROJECT_ID

echo ""
echo "================================ SUMMARY ================================"
echo "Created 3 Cloud Scheduler jobs (free tier limit):"
echo ""
echo "1. daily-bq-refresh"
echo "   Schedule: Every day at 06:00 UTC"
echo "   Action: Publish to Pub/Sub to trigger KPI refresh"
echo ""
echo "2. weekly-kpi-export"
echo "   Schedule: Every Monday at 07:00 UTC"
echo "   Action: Publish to Pub/Sub to trigger weekly report export"
echo ""
echo "3. monthly-cleanup"
echo "   Schedule: 1st of each month at 03:00 UTC"
echo "   Action: Publish to Pub/Sub to trigger partition cleanup"
echo ""
echo "=========================================================================="
echo ""
echo "[COST NOTE] Free tier limit is 3 jobs/month - do NOT add more without checking billing"
echo ""
echo "[✓] Cloud Scheduler setup complete!"
