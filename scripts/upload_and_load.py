"""
Upload cleaned data to GCS, then load to BigQuery from GCS
"""

import sys
import os
from pathlib import Path
from google.cloud import storage, bigquery
import pandas as pd

# Configuration
PROJECT_ID = "ecommerce-494010"
BUCKET_NAME = "ecommerce-494010-data"
DATASET = "ecommerce_analytics"
CLEAN_DATA_DIR = Path("data/clean")

FILE_TABLE_MAP = {
    "clients_clean.csv": "clients",
    "products_clean.csv": "products",
    "orders_clean.csv": "orders",
    "order_items_clean.csv": "order_items",
    "incidents_clean.csv": "incidents",
    "page_views_clean.csv": "page_views",
}


def upload_to_gcs(csv_path: Path) -> str:
    """Upload CSV to GCS and return GCS URI"""
    
    print(f"Uploading {csv_path.name} to GCS...")
    
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    
    # Use csv filename as object name
    blob = bucket.blob(f"data/{csv_path.name}")
    blob.upload_from_filename(csv_path)
    
    gcs_uri = f"gs://{BUCKET_NAME}/data/{csv_path.name}"
    print(f"✅ Uploaded to {gcs_uri}\n")
    
    return gcs_uri


def load_from_gcs_to_bq(table_name: str, gcs_uri: str) -> bool:
    """Load from GCS to BigQuery"""
    
    print(f"Loading {table_name} from GCS...")
    
    bq_client = bigquery.Client(project=PROJECT_ID)
    table_id = f"{PROJECT_ID}.{DATASET}.{table_name}"
    
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
        write_disposition="WRITE_TRUNCATE",
    )
    
    try:
        load_job = bq_client.load_table_from_uri(
            gcs_uri,
            table_id,
            job_config=job_config,
        )
        
        load_job.result()  # Wait for job
        
        table = bq_client.get_table(table_id)
        print(f"✅ {table_name}: {table.num_rows:,} rows loaded\n")
        return True
        
    except Exception as e:
        print(f"❌ Error loading {table_name}: {str(e)}\n")
        return False


def main():
    """Execute upload and load pipeline"""
    
    print("=" * 70)
    print("GCS Upload → BigQuery Load Pipeline")
    print("=" * 70)
    print(f"Project: {PROJECT_ID}")
    print(f"Bucket: {BUCKET_NAME}")
    print(f"Dataset: {DATASET}")
    print()
    
    # Verify local directory
    if not CLEAN_DATA_DIR.exists():
        print(f"❌ ERROR: {CLEAN_DATA_DIR} not found!")
        print("Please run from project root with cleaned data.")
        return 1
    
    results = {}
    
    # For each CSV: Upload to GCS, then load to BigQuery
    for file_name, table_name in FILE_TABLE_MAP.items():
        csv_path = CLEAN_DATA_DIR / file_name
        
        if not csv_path.exists():
            print(f"❌ File not found: {csv_path}\n")
            results[table_name] = False
            continue
        
        try:
            # Step 1: Upload to GCS
            gcs_uri = upload_to_gcs(csv_path)
            
            # Step 2: Load from GCS to BigQuery
            success = load_from_gcs_to_bq(table_name, gcs_uri)
            results[table_name] = success
            
        except Exception as e:
            print(f"❌ Pipeline error for {table_name}: {str(e)}\n")
            results[table_name] = False
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    successful = sum(1 for v in results.values() if v)
    total = len(results)
    
    for table_name, success in results.items():
        status = "✅ OK" if success else "❌ FAILED"
        print(f"  {table_name:15} {status}")
    
    print(f"\nTotal: {successful}/{total} tables loaded")
    print("=" * 70)
    
    if successful == total:
        print("✅ All data loaded! Ready for Looker Studio.")
        return 0
    else:
        print(f"❌ {total - successful} tables failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
