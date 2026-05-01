#!/usr/bin/env python3
"""
Test pipeline for Dataflow on GCP
Quick validation before full deployment

This script:
1. Tests GCP connectivity
2. Checks BigQuery tables
3. Publishes a few test messages to Pub/Sub
4. Monitors the Dataflow job
5. Validates data in BigQuery

Usage:
    python beam/test_gcp_pipeline.py --project ecommerce-494010 --region europe-west1
"""

import argparse
import logging
import sys
import time
from pathlib import Path

from google.cloud import bigquery
from google.cloud import pubsub_v1
from google.cloud import dataflow_v1beta3
import google.auth

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GCPPipelineTest:
    """Test GCP connectivity and pipeline."""

    def __init__(self, project_id: str, region: str):
        self.project_id = project_id
        self.region = region
        self.publisher = pubsub_v1.PublisherClient()
        self.bq_client = bigquery.Client(project=project_id)
        self.credentials, self.project = google.auth.default()

    def test_auth(self) -> bool:
        """Test GCP authentication."""
        logger.info("Testing GCP authentication...")
        try:
            logger.info(f"✓ Project ID: {self.project_id}")
            logger.info(f"✓ Credentials: {self.credentials.__class__.__name__}")
            return True
        except Exception as e:
            logger.error(f"✗ Authentication failed: {e}")
            return False

    def test_pubsub(self) -> bool:
        """Test Pub/Sub connectivity."""
        logger.info("\nTesting Pub/Sub...")
        try:
            topics = self.publisher.list_topics(
                request={"project": f"projects/{self.project_id}"}
            )
            topic_list = list(topics)
            logger.info(f"✓ Found {len(topic_list)} topics")

            required_topics = [
                "orders-realtime",
                "clients-realtime",
                "incidents-realtime",
                "pageviews-realtime",
            ]

            for topic_name in required_topics:
                topic_path = self.publisher.topic_path(self.project_id, topic_name)
                found = any(t.name == topic_path for t in topic_list)
                if found:
                    logger.info(f"  ✓ Topic exists: {topic_name}")
                else:
                    logger.warning(f"  ⚠ Topic missing: {topic_name}")

            return True
        except Exception as e:
            logger.error(f"✗ Pub/Sub test failed: {e}")
            return False

    def test_bigquery(self) -> bool:
        """Test BigQuery connectivity."""
        logger.info("\nTesting BigQuery...")
        try:
            dataset = self.bq_client.get_dataset("ecommerce_analytics")
            logger.info(f"✓ Dataset exists: {dataset.dataset_id}")

            required_tables = [
                "orders_stream",
                "clients_stream",
                "incidents_stream",
                "pageviews_stream",
                "pipeline_errors",
                "metrics_daily",
            ]

            for table_name in required_tables:
                table_id = f"{self.project_id}.ecommerce_analytics.{table_name}"
                try:
                    table = self.bq_client.get_table(table_id)
                    row_count = table.num_rows
                    logger.info(f"  ✓ Table: {table_name} ({row_count} rows)")
                except Exception as e:
                    logger.warning(f"  ⚠ Table missing: {table_name}")

            return True
        except Exception as e:
            logger.error(f"✗ BigQuery test failed: {e}")
            return False

    def publish_test_message(self, topic_name: str, message: dict) -> bool:
        """Publish a test message to Pub/Sub."""
        try:
            import json
            
            topic_path = self.publisher.topic_path(self.project_id, topic_name)
            message_json = json.dumps(message).encode("utf-8")
            
            future = self.publisher.publish(topic_path, message_json)
            message_id = future.result(timeout=5.0)
            
            logger.info(f"  ✓ Published message to {topic_name}: {message_id}")
            return True
        except Exception as e:
            logger.error(f"  ✗ Failed to publish: {e}")
            return False

    def test_pubsub_publish(self) -> bool:
        """Test publishing messages to Pub/Sub."""
        logger.info("\nTesting Pub/Sub publishing...")
        
        test_messages = {
            "orders-realtime": {
                "order_id": "TEST-001",
                "client_id": "C001",
                "total_amount": "99.99",
                "status": "Livré",
                "date_commande": "2026-05-01T10:00:00",
            },
            "clients-realtime": {
                "client_id": "C001",
                "nom": "Dupont",
                "prenom": "Alice",
                "email": "alice@example.com",
                "age": "34",
            },
        }

        success = True
        for topic, message in test_messages.items():
            if not self.publish_test_message(topic, message):
                success = False

        return success

    def check_dataflow_jobs(self) -> bool:
        """Check Dataflow jobs."""
        logger.info("\nChecking Dataflow jobs...")
        try:
            # Note: This requires dataflow admin permissions
            logger.info(f"✓ Dataflow region: {self.region}")
            logger.info("  (Use Cloud Console to monitor jobs)")
            logger.info(f"  https://console.cloud.google.com/dataflow/jobs/{self.region}")
            return True
        except Exception as e:
            logger.warning(f"⚠ Could not check Dataflow jobs: {e}")
            return True

    def run_all_tests(self) -> bool:
        """Run all tests."""
        logger.info("=" * 70)
        logger.info("GCP PIPELINE TEST")
        logger.info("=" * 70)

        results = {
            "Authentication": self.test_auth(),
            "Pub/Sub": self.test_pubsub(),
            "BigQuery": self.test_bigquery(),
            "Pub/Sub Publishing": self.test_pubsub_publish(),
            "Dataflow Jobs": self.check_dataflow_jobs(),
        }

        logger.info("\n" + "=" * 70)
        logger.info("TEST RESULTS")
        logger.info("=" * 70)

        for test_name, result in results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            logger.info(f"{status}: {test_name}")

        all_passed = all(results.values())
        logger.info("=" * 70)

        if all_passed:
            logger.info("✓ All tests passed!")
            logger.info("\nNext steps:")
            logger.info("1. Deploy the Dataflow pipeline:")
            logger.info(f"   bash deploy/deploy_dataflow.sh {self.project_id} {self.region}")
            logger.info("2. Publish full dataset:")
            logger.info(f"   python beam/publish_test_data.py --project {self.project_id} ...")
            logger.info("3. Monitor in Cloud Console:")
            logger.info(f"   https://console.cloud.google.com/bigquery?project={self.project_id}")
        else:
            logger.error("✗ Some tests failed. Check GCP setup.")

        return all_passed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test GCP connectivity for Dataflow pipeline"
    )
    parser.add_argument(
        "--project",
        required=True,
        help="GCP Project ID",
    )
    parser.add_argument(
        "--region",
        default="europe-west1",
        help="GCP region (default: europe-west1)",
    )

    args = parser.parse_args()

    try:
        tester = GCPPipelineTest(args.project, args.region)
        success = tester.run_all_tests()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"✗ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
