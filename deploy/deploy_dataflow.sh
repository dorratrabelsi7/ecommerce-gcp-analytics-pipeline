#!/bin/bash
# Automated GCP deployment for eCommerce Analytics Pipeline
# This script sets up all required GCP resources and deploys the Dataflow pipeline

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================="
echo "eCommerce Analytics Pipeline - GCP Deployment"
echo "==================================================${NC}"
echo ""

# Configuration
PROJECT_ID="${1:-ecommerce-494010}"
REGION="${2:-europe-west1}"
BUCKET_NAME="ecommerce-analytics-${PROJECT_ID}-${RANDOM}"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Bucket: $BUCKET_NAME"
echo ""

# Step 1: Authentication
echo -e "${BLUE}[1/8] Verifying GCP authentication...${NC}"
if ! gcloud auth list 2>/dev/null | grep -q "ACTIVE"; then
    echo -e "${YELLOW}Please authenticate with GCP:${NC}"
    gcloud auth login
    gcloud auth application-default login
else
    echo -e "${GREEN}✓ GCP authentication verified${NC}"
fi
echo ""

# Step 2: Set project
echo -e "${BLUE}[2/8] Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID 2>&1 | grep -v "^Updated"
echo -e "${GREEN}✓ Project set to: $PROJECT_ID${NC}"
echo ""

# Step 3: Enable APIs
echo -e "${BLUE}[3/8] Enabling required GCP APIs...${NC}"
echo "  Enabling: dataflow, pubsub, bigquery, storage, logging..."
gcloud services enable dataflow.googleapis.com \
    pubsub.googleapis.com \
    bigquery.googleapis.com \
    storage-api.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com \
    --quiet 2>&1 | grep -v "^Operation"
echo -e "${GREEN}✓ APIs enabled${NC}"
echo ""

# Step 4: Create Cloud Storage bucket
echo -e "${BLUE}[4/8] Creating Cloud Storage bucket...${NC}"
if ! gsutil ls gs://$BUCKET_NAME 2>/dev/null; then
    gsutil mb -l $REGION gs://$BUCKET_NAME
    gsutil mb -l $REGION gs://$BUCKET_NAME/temp/
    gsutil mb -l $REGION gs://$BUCKET_NAME/input/
    gsutil mb -l $REGION gs://$BUCKET_NAME/output/
    echo -e "${GREEN}✓ Bucket created: gs://$BUCKET_NAME${NC}"
else
    echo -e "${YELLOW}⚠ Bucket already exists: gs://$BUCKET_NAME${NC}"
fi
echo ""

# Step 5: Create Pub/Sub topics and subscriptions
echo -e "${BLUE}[5/8] Creating Pub/Sub topics and subscriptions...${NC}"

TOPICS=("orders-realtime" "clients-realtime" "incidents-realtime" "pageviews-realtime")

for topic in "${TOPICS[@]}"; do
    if ! gcloud pubsub topics describe $topic 2>/dev/null > /dev/null; then
        gcloud pubsub topics create $topic
        echo -e "${GREEN}  ✓ Created topic: $topic${NC}"
    else
        echo -e "${YELLOW}  ⚠ Topic exists: $topic${NC}"
    fi

    # Create subscription
    sub_name="${topic%-*}-sub"
    if ! gcloud pubsub subscriptions describe $sub_name 2>/dev/null > /dev/null; then
        gcloud pubsub subscriptions create $sub_name --topic $topic
        echo -e "${GREEN}  ✓ Created subscription: $sub_name${NC}"
    else
        echo -e "${YELLOW}  ⚠ Subscription exists: $sub_name${NC}"
    fi
done
echo ""

# Step 6: Create BigQuery dataset and tables
echo -e "${BLUE}[6/8] Creating BigQuery dataset and tables...${NC}"

# Create dataset
if ! bq ls -d --project_id=$PROJECT_ID | grep -q "ecommerce_analytics"; then
    bq mk --dataset \
        --description "eCommerce Analytics Data Warehouse" \
        --location EU \
        ecommerce_analytics
    echo -e "${GREEN}✓ Created dataset: ecommerce_analytics${NC}"
else
    echo -e "${YELLOW}⚠ Dataset already exists${NC}"
fi

# Create tables
TABLES=(
    "orders_stream:beam/schemas/orders_schema.json"
    "clients_stream:beam/schemas/clients_schema.json"
    "incidents_stream:beam/schemas/incidents_schema.json"
    "pageviews_stream:beam/schemas/pageviews_schema.json"
    "pipeline_errors:beam/schemas/errors_schema.json"
    "metrics_daily:beam/schemas/metrics_schema.json"
)

for table_config in "${TABLES[@]}"; do
    IFS=':' read -r table_name schema_file <<< "$table_config"
    
    if ! bq ls -t --project_id=$PROJECT_ID ecommerce_analytics | grep -q "$table_name"; then
        if [ -f "$schema_file" ]; then
            bq mk --table \
                ecommerce_analytics.$table_name \
                $schema_file
            echo -e "${GREEN}  ✓ Created table: $table_name${NC}"
        else
            echo -e "${YELLOW}  ⚠ Schema file not found: $schema_file${NC}"
        fi
    else
        echo -e "${YELLOW}  ⚠ Table exists: $table_name${NC}"
    fi
done
echo ""

# Step 7: Deploy Dataflow pipeline
echo -e "${BLUE}[7/8] Deploying Dataflow pipeline...${NC}"
echo "  Pipeline: beam/dataflow_pipeline_gcp.py"
echo "  Region: $REGION"
echo "  Temp location: gs://$BUCKET_NAME/temp/"
echo ""

if [ ! -f "beam/dataflow_pipeline_gcp.py" ]; then
    echo -e "${RED}✗ Pipeline file not found: beam/dataflow_pipeline_gcp.py${NC}"
    exit 1
fi

python beam/dataflow_pipeline_gcp.py \
    --project $PROJECT_ID \
    --region $REGION \
    --temp-location gs://$BUCKET_NAME/temp/ \
    2>&1 | tee deployment.log

echo -e "${GREEN}✓ Pipeline deployed${NC}"
echo ""

# Step 8: Verify deployment
echo -e "${BLUE}[8/8] Verifying deployment...${NC}"

# Get latest job ID
JOB_ID=$(gcloud dataflow jobs list --region=$REGION --limit=1 --format="value(id)")

if [ -n "$JOB_ID" ]; then
    echo -e "${GREEN}✓ Dataflow job submitted: $JOB_ID${NC}"
    echo ""
    echo -e "${BLUE}Monitoring URLs:${NC}"
    echo "  Dataflow Console:"
    echo "    https://console.cloud.google.com/dataflow/jobs/$REGION/$JOB_ID"
    echo ""
    echo "  BigQuery:"
    echo "    https://console.cloud.google.com/bigquery?project=$PROJECT_ID"
    echo ""
    echo "  Pub/Sub:"
    echo "    https://console.cloud.google.com/pubsub/topiclist?project=$PROJECT_ID"
else
    echo -e "${YELLOW}⚠ Could not retrieve job ID${NC}"
fi

echo ""
echo -e "${BLUE}=================================================="
echo "Deployment complete!"
echo "==================================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Monitor the pipeline in the Dataflow console"
echo "2. Publish test data:"
echo "   python beam/publish_test_data.py \\"
echo "     --project $PROJECT_ID \\"
echo "     --input data/raw/orders.csv \\"
echo "     --topic orders-realtime \\"
echo "     --rate 5"
echo "3. Check BigQuery for incoming data:"
echo "   bq query 'SELECT COUNT(*) as total FROM \`$PROJECT_ID.ecommerce_analytics.orders_stream\`'"
echo "4. Create Looker Studio dashboard connected to BigQuery"
echo ""
echo -e "${YELLOW}Cleanup (if needed):${NC}"
echo "  bash deploy/cleanup_gcp.sh $PROJECT_ID"
echo ""

exit 0
