"""
Cost-free health check for e-commerce analytics pipeline.

Checks pipeline component status using only free tools:
- BigQuery queries (partition-filtered)
- gcloud CLI (no API costs)
- Cloud Logging (free tier)

Author: Dorra Trabelsi
Date: 2026-04-21

COST NOTE: This script uses only gcloud CLI and partition-filtered BQ queries.
No Cloud Monitoring API is called. Estimated query cost: < 1MB scanned = $0.
"""

import sys
import logging
import json
import subprocess
from datetime import datetime, timedelta

from google.cloud import bigquery, logging as cloud_logging
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = os.getenv("PROJECT_ID", "ecommerce-494010")
DATASET = os.getenv("DATASET", "ecommerce_analytics")
PUBSUB_SUB = os.getenv("PUBSUB_SUB", "orders-sub")


def check_bigquery_tables():
    """Check row counts in BigQuery tables."""
    logger.info("Checking BigQuery tables...")
    
    client = bigquery.Client(project=PROJECT_ID)
    status = {"component": "BigQuery", "status": "OK", "details": {}}
    
    try:
        tables = ["clients", "products", "orders", "order_items", "incidents", "page_views"]
        
        for table in tables:
            query = f"""
            SELECT COUNT(*) as row_count
            FROM `{PROJECT_ID}.{DATASET}.{table}`
            WHERE 1=1
            """
            
            # Add partition filter for time-based tables
            if table in ["orders", "order_items", "incidents", "page_views"]:
                partition_col = "order_date" if table in ["orders", "order_items"] else \
                                "report_date" if table == "incidents" else "event_datetime"
                query += f" AND DATE({partition_col}) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)"
            
            result = client.query(query, job_config=bigquery.QueryJobConfig(
                use_query_cache=False,
                maximum_bytes_billed=1024*1024,  # 1 MB max
            )).result()
            
            row_count = list(result)[0].row_count
            status["details"][table] = row_count
            
            if row_count > 0:
                logger.info(f"  ✓ {table}: {row_count:,} rows")
            else:
                logger.warning(f"  ⚠ {table}: 0 rows")
        
    except Exception as e:
        status["status"] = "ERROR"
        status["error"] = str(e)
        logger.error(f"  ✗ BigQuery check failed: {str(e)}")
    
    return status


def check_pubsub_backlog():
    """Check Pub/Sub subscription backlog."""
    logger.info("Checking Pub/Sub backlog...")
    
    status = {"component": "Pub/Sub", "status": "OK"}
    
    try:
        result = subprocess.run(
            [
                "gcloud", "pubsub", "subscriptions", "describe", PUBSUB_SUB,
                "--format=value(num_undelivered_messages)",
                f"--project={PROJECT_ID}"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            backlog = int(result.stdout.strip())
            status["backlog"] = backlog
            
            if backlog > 0:
                logger.warning(f"  ⚠ Pub/Sub backlog: {backlog} undelivered messages")
                status["status"] = "WARNING"
            else:
                logger.info(f"  ✓ Pub/Sub backlog: 0 (clear)")
        else:
            logger.warning(f"  ⚠ Could not query backlog: {result.stderr}")
            status["status"] = "WARNING"
    
    except Exception as e:
        status["status"] = "ERROR"
        status["error"] = str(e)
        logger.error(f"  ✗ Pub/Sub check failed: {str(e)}")
    
    return status


def check_cloud_function_logs():
    """Check recent Cloud Function errors."""
    logger.info("Checking Cloud Function logs...")
    
    status = {"component": "Cloud Functions", "status": "OK"}
    
    try:
        result = subprocess.run(
            [
                "gcloud", "logging", "read",
                'resource.type="cloud_function" AND severity>=ERROR',
                "--limit=5",
                "--format=json",
                f"--project={PROJECT_ID}"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            if result.stdout.strip():
                logs = json.loads(result.stdout)
                error_count = len(logs)
                logger.warning(f"  ⚠ Recent errors: {error_count}")
                status["recent_errors"] = error_count
                status["status"] = "WARNING"
            else:
                logger.info(f"  ✓ Cloud Function: No recent errors")
        else:
            logger.warning(f"  ⚠ Could not query logs: {result.stderr}")
    
    except Exception as e:
        status["status"] = "ERROR"
        status["error"] = str(e)
        logger.error(f"  ✗ Cloud Function check failed: {str(e)}")
    
    return status


def print_summary(checks):
    """Print health check summary."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("PIPELINE HEALTH CHECK SUMMARY")
    logger.info("=" * 80)
    
    for check in checks:
        component = check["component"]
        status = check["status"]
        icon = "✓" if status == "OK" else "⚠" if status == "WARNING" else "✗"
        color = "\033[92m" if status == "OK" else "\033[93m" if status == "WARNING" else "\033[91m"
        reset = "\033[0m"
        
        logger.info(f"{color}{icon} {component}: {status}{reset}")
    
    logger.info("=" * 80)
    logger.info("")


def main():
    """Run health check."""
    try:
        logger.info("Starting pipeline health check...")
        logger.info("")
        
        checks = [
            check_bigquery_tables(),
            check_pubsub_backlog(),
            check_cloud_function_logs(),
        ]
        
        print_summary(checks)
        
        # Determine overall status
        overall_status = "OK"
        if any(c["status"] == "ERROR" for c in checks):
            overall_status = "ERROR"
        elif any(c["status"] == "WARNING" for c in checks):
            overall_status = "WARNING"
        
        logger.info(f"Overall status: {overall_status}")
        
        return 0 if overall_status == "OK" else 1
    
    except Exception as e:
        logger.error(f"✗ Health check failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
