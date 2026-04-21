#!/bin/bash

# ============================================================================
# BIGQUERY DATA LOADING SCRIPT
# Upload cleaned CSVs from local storage to BigQuery
# ============================================================================

set -e

PROJECT_ID="ecommerce-494010"
DATASET="ecommerce_analytics"

echo "======================================================================"
echo "BigQuery Data Loading - E-Commerce Analytics Pipeline"
echo "======================================================================"
echo "Project: $PROJECT_ID"
echo "Dataset: $DATASET"
echo ""

# Ensure we're in the correct directory
if [ ! -d "data/clean" ]; then
    echo "❌ ERROR: data/clean directory not found!"
    echo "Please run from project root directory."
    exit 1
fi

# Function to load a single table
load_table() {
    local table_name=$1
    local csv_file=$2
    
    echo "Loading: $table_name from $csv_file..."
    
    if [ ! -f "$csv_file" ]; then
        echo "❌ File not found: $csv_file"
        return 1
    fi
    
    bq load \
        --autodetect \
        --source_format=CSV \
        --skip_leading_rows=1 \
        --allow_quoted_newlines \
        --allow_jagged_rows \
        "$DATASET.$table_name" \
        "$csv_file"
    
    echo "✅ $table_name loaded successfully"
    echo ""
}

# Load all tables
load_table "clients" "data/clean/clients_clean.csv"
load_table "products" "data/clean/products_clean.csv"
load_table "orders" "data/clean/orders_clean.csv"
load_table "order_items" "data/clean/order_items_clean.csv"
load_table "incidents" "data/clean/incidents_clean.csv"
load_table "page_views" "data/clean/page_views_clean.csv"

# Verify data
echo "======================================================================"
echo "Verification - Row Counts"
echo "======================================================================"

bq query --use_legacy_sql=false "
SELECT
  'clients' as table_name, COUNT(*) as row_count FROM $DATASET.clients
UNION ALL
SELECT 'products', COUNT(*) FROM $DATASET.products
UNION ALL
SELECT 'orders', COUNT(*) FROM $DATASET.orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM $DATASET.order_items
UNION ALL
SELECT 'incidents', COUNT(*) FROM $DATASET.incidents
UNION ALL
SELECT 'page_views', COUNT(*) FROM $DATASET.page_views
ORDER BY table_name;
"

echo ""
echo "======================================================================"
echo "✅ All data loaded successfully!"
echo "======================================================================"
