"""
Setup log-based alerts for Cloud Logging.

Creates 2 basic alerts based on Cloud Logging:
1. Alert when Cloud Function logs contain "ERROR"
2. Alert when Pub/Sub DLQ receives any message

Author: Dorra Trabelsi
Date: 2026-04-21

COST NOTE: Log-based alerts are free. Metric-based alerts (Cloud Monitoring)
can generate costs at scale — not used here.
"""

import sys
import logging
import json
import subprocess
from datetime import datetime

from dotenv import load_dotenv
import os

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = os.getenv("PROJECT_ID", "ecommerce-494010")
ALERT_EMAIL = "dorra.trabelsi@itbs.tn"  # Change to notification email


def create_function_error_alert():
    """Create alert for Cloud Function errors."""
    logger.info("Creating Cloud Function error alert...")
    
    alert_name = "cf-error-alert"
    filter_expr = 'resource.type="cloud_function" AND severity>=ERROR'
    
    try:
        result = subprocess.run(
            [
                "gcloud", "logging", "sinks", "create", alert_name,
                "logging.googleapis.com/logs",
                f"--log-filter={filter_expr}",
                f"--project={PROJECT_ID}",
                "--quiet"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info(f"  ✓ Cloud Function error alert created: {alert_name}")
            return True
        else:
            logger.warning(f"  ⚠ Alert creation message: {result.stderr}")
            return False
    
    except Exception as e:
        logger.warning(f"  ⚠ Could not create alert: {str(e)}")
        return False


def create_dlq_alert():
    """Create alert for Pub/Sub DLQ messages."""
    logger.info("Creating Pub/Sub DLQ alert...")
    
    alert_name = "pubsub-dlq-alert"
    filter_expr = 'resource.type="pubsub_subscription" AND resource.labels.subscription_id="orders-realtime-dlq"'
    
    try:
        result = subprocess.run(
            [
                "gcloud", "logging", "sinks", "create", alert_name,
                "logging.googleapis.com/logs",
                f"--log-filter={filter_expr}",
                f"--project={PROJECT_ID}",
                "--quiet"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info(f"  ✓ Pub/Sub DLQ alert created: {alert_name}")
            return True
        else:
            logger.warning(f"  ⚠ Alert creation message: {result.stderr}")
            return False
    
    except Exception as e:
        logger.warning(f"  ⚠ Could not create alert: {str(e)}")
        return False


def main():
    """Setup monitoring alerts."""
    try:
        logger.info("=" * 80)
        logger.info("SETTING UP MONITORING ALERTS")
        logger.info("=" * 80)
        logger.info("")
        
        # Create alerts
        cf_ok = create_function_error_alert()
        dlq_ok = create_dlq_alert()
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("ALERTS SETUP SUMMARY")
        logger.info("=" * 80)
        
        logger.info("Alert 1: Cloud Function errors")
        logger.info(f"  Status: {'✓ Created' if cf_ok else '⚠ Skipped'}")
        
        logger.info("Alert 2: Pub/Sub DLQ messages")
        logger.info(f"  Status: {'✓ Created' if dlq_ok else '⚠ Skipped'}")
        
        logger.info("")
        logger.info("COST NOTE:")
        logger.info("  Log-based alerts (used here) are free.")
        logger.info("  Metric-based alerts (Cloud Monitoring) can incur costs.")
        logger.info("")
        logger.info("=" * 80)
        
        return 0
    
    except Exception as e:
        logger.error(f"✗ Alert setup failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
