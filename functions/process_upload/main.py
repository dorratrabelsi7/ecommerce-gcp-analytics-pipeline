"""
Cloud Function: Process GCS upload and load to BigQuery

This function is triggered when a file is uploaded to Cloud Storage.
It processes the file and loads it into BigQuery.

Author: Dorra Trabelsi
Date: 2026-04-21

COST NOTE: Cloud Functions gen2 free tier = 2M invocations/month.
This function is only triggered on file upload, not on a schedule.
Expected invocations: < 100/month → always free.
"""

import json
import logging
import os
from datetime import datetime
from io import BytesIO

import functions_framework
from google.cloud import bigquery, storage, pubsub_v1

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize clients
storage_client = storage.Client()
bq_client = bigquery.Client()
publisher = pubsub_v1.PublisherClient()

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID", "ecommerce-494010")
DATASET = os.getenv("DATASET", "ecommerce_analytics")
DLQ_TOPIC = f"projects/{PROJECT_ID}/topics/orders-realtime-dlq"

# Filename to table mapping
FILE_TO_TABLE = {
    "clients_clean.csv": "clients",
    "products_clean.csv": "products",
    "orders_clean.csv": "orders",
    "order_items_clean.csv": "order_items",
    "incidents_clean.csv": "incidents",
    "page_views_clean.csv": "page_views",
}


@functions_framework.cloud_event
def process_upload(cloud_event):
    """
    Process a GCS file upload event and load to BigQuery.
    
    Args:
        cloud_event: CloudEvent object with storage details
    
    Returns:
        HTTP response with processing status
    """
    try:
        # Parse event
        data = cloud_event.data
        bucket_name = data["bucket"]
        file_name = data["name"]
        
        logger.info(f"Processing file: gs://{bucket_name}/{file_name}")
        
        # Check if file should be processed
        if file_name not in FILE_TO_TABLE:
            logger.warning(f"Unknown file type: {file_name}")
            return {"status": "skipped", "reason": "unknown_file_type"}, 200
        
        table_id = FILE_TO_TABLE[file_name]
        start_time = datetime.now()
        
        # Download file from GCS
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        csv_data = blob.download_as_bytes()
        
        logger.info(f"Downloaded {len(csv_data)} bytes from GCS")
        
        # Load to BigQuery
        table_ref = bq_client.dataset(DATASET).table(table_id)
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=True,
            write_disposition="WRITE_APPEND",
        )
        
        load_job = bq_client.load_table_from_file(
            BytesIO(csv_data),
            table_ref,
            job_config=job_config,
        )
        
        # Wait for job completion
        load_job.result()
        
        # Get row count
        table = bq_client.get_table(table_ref)
        rows_loaded = table.num_rows
        
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        logger.info(f"✓ Loaded {rows_loaded} rows to {table_id} in {processing_time_ms:.0f}ms")
        
        # Publish confirmation to Pub/Sub
        confirmation_message = {
            "filename": file_name,
            "table": table_id,
            "nb_rows_inserted": rows_loaded,
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "processing_time_ms": processing_time_ms,
        }
        
        publisher.publish(
            DLQ_TOPIC,
            json.dumps(confirmation_message).encode("utf-8"),
        )
        
        return {
            "status": "success",
            "table": table_id,
            "rows_loaded": rows_loaded,
            "processing_time_ms": processing_time_ms,
        }, 200
    
    except Exception as e:
        logger.error(f"✗ Error processing file: {str(e)}", exc_info=True)
        
        # Publish error to DLQ
        error_message = {
            "filename": file_name,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "status": "error",
        }
        
        publisher.publish(
            DLQ_TOPIC,
            json.dumps(error_message).encode("utf-8"),
        )
        
        # Return 200 to acknowledge event processing (even on error)
        return {"status": "error", "error": str(e)}, 200
