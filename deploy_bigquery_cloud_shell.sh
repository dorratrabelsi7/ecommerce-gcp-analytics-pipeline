#!/bin/bash
# Cloud Shell setup script - Deploy BigQuery schema

echo "======================================================================"
echo "BIGQUERY SCHEMA DEPLOYMENT - CLOUD SHELL"
echo "======================================================================"

PROJECT_ID="ecommerce-494010"
DATASET="ecommerce_analytics"

echo ""
echo "[STEP 1] Setting project..."
gcloud config set project $PROJECT_ID
echo "✅ Project set"

echo ""
echo "[STEP 2] Creating BigQuery dataset..."
bq mk --dataset --location=EU $DATASET
echo "✅ Dataset created"

echo ""
echo "[STEP 3] Creating tables..."
bq query --use_legacy_sql=false < sql/01_create_tables_clean.sql
echo "✅ Tables created"

echo ""
echo "[STEP 4] Creating views..."
bq query --use_legacy_sql=false < sql/02_create_views_clean.sql
echo "✅ Views created"

echo ""
echo "[STEP 5] Verifying..."
bq ls $DATASET

echo ""
echo "======================================================================"
echo "✅ BIGQUERY SCHEMA DEPLOYMENT COMPLETE!"
echo "======================================================================"
