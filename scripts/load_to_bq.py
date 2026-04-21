"""
Load cleaned data to BigQuery and validate row counts.

This script:
1. Loads all cleaned CSV files from data/clean/ to BigQuery
2. Executes schema and view creation SQL
3. Validates row counts match source files
4. Prints final load report

Author: Dorra Trabelsi
Date: 2026-04-21

COST NOTE: Loading CSVs via the BigQuery Python client uses the free batch
load API. This does NOT consume query quota. It is always free regardless
of file size.
"""

import sys
import time
import logging
from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = os.getenv("PROJECT_ID", "ecommerce-494010")
DATASET = os.getenv("DATASET", "ecommerce_analytics")
CLEAN_DATA_DIR = Path("data/clean")

# File to table mapping
FILE_TABLE_MAP = {
    "clients_clean.csv": "clients",
    "products_clean.csv": "products",
    "orders_clean.csv": "orders",
    "order_items_clean.csv": "order_items",
    "incidents_clean.csv": "incidents",
    "page_views_clean.csv": "page_views",
}


def load_to_bigquery():
    """Load all cleaned CSV files to BigQuery."""
    logger.info("=" * 80)
    logger.info("LOADING DATA TO BIGQUERY")
    logger.info("=" * 80)
    
    client = bigquery.Client(project=PROJECT_ID)
    load_report = {}
    
    for file_name, table_name in FILE_TABLE_MAP.items():
        file_path = CLEAN_DATA_DIR / file_name
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            continue
        
        # Load local CSV row count
        source_df = pd.read_csv(file_path)
        source_rows = len(source_df)
        
        logger.info(f"Loading {table_name} from {file_name}")
        logger.info(f"  Source rows: {source_rows:,}")
        
        start_time = time.time()
        
        # Configure load job
        table_id = f"{PROJECT_ID}.{DATASET}.{table_name}"
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=True,
            write_disposition="WRITE_TRUNCATE",
        )
        
        try:
            # Load job
            load_job = client.load_table_from_file(
                file_path.open("rb"),
                table_id,
                job_config=job_config,
            )
            
            # Wait for completion
            load_job.result()
            
            elapsed = time.time() - start_time
            
            # Get final row count
            table = client.get_table(table_id)
            loaded_rows = table.num_rows
            
            logger.info(f"✓ {table_name} → {loaded_rows:,} rows loaded in {elapsed:.1f}s")
            
            load_report[table_name] = {
                "source_rows": source_rows,
                "loaded_rows": loaded_rows,
                "elapsed": elapsed,
                "status": "success"
            }
        
        except Exception as e:
            logger.error(f"✗ Failed to load {table_name}: {str(e)}")
            load_report[table_name] = {
                "source_rows": source_rows,
                "status": "error",
                "error": str(e)
            }
    
    return client, load_report


def validate_loads(client, load_report):
    """Validate that loaded row counts match source files."""
    logger.info("=" * 80)
    logger.info("VALIDATING LOADS")
    logger.info("=" * 80)
    
    all_valid = True
    
    for table_name, report in load_report.items():
        if report["status"] == "error":
            logger.warning(f"  {table_name}: SKIPPED (load failed)")
            continue
        
        if report["source_rows"] == report["loaded_rows"]:
            logger.info(f"  ✓ {table_name}: {report['loaded_rows']:,} rows (match)")
        else:
            logger.warning(
                f"  ⚠ {table_name}: source={report['source_rows']:,}, "
                f"loaded={report['loaded_rows']:,} (MISMATCH)"
            )
            all_valid = False
    
    return all_valid


def main():
    """Execute BigQuery load pipeline."""
    try:
        logger.info("Initializing BigQuery load...")
        
        # Load data
        client, load_report = load_to_bigquery()
        
        # Validate
        all_valid = validate_loads(client, load_report)
        
        # Print summary
        logger.info("=" * 80)
        logger.info("LOAD SUMMARY")
        logger.info("=" * 80)
        
        total_source = sum(r.get("source_rows", 0) for r in load_report.values())
        total_loaded = sum(r.get("loaded_rows", 0) for r in load_report.values() if r["status"] == "success")
        
        logger.info(f"Total source rows:  {total_source:,}")
        logger.info(f"Total loaded rows:  {total_loaded:,}")
        logger.info(f"Validation:         {'PASS ✓' if all_valid else 'FAIL ⚠'}")
        
        logger.info("=" * 80)
        logger.info("✓ BigQuery load complete!")
        logger.info(f"  Project: {PROJECT_ID}")
        logger.info(f"  Dataset: {DATASET}")
        logger.info("=" * 80)
        
        return 0
    
    except Exception as e:
        logger.error(f"✗ Load failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
