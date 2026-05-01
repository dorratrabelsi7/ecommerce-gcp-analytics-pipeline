#!/usr/bin/env python3
"""
Publisher for simulating real-time data to Pub/Sub

This script:
1. Reads CSV/JSON data files
2. Publishes them as JSON messages to Pub/Sub
3. Simulates real-time data streaming

Usage:
    python beam/publish_test_data.py \
        --project ecommerce-494010 \
        --input data/raw/orders.csv \
        --topic orders-realtime \
        --rate 5  # messages per second
    
    python beam/publish_test_data.py \
        --project ecommerce-494010 \
        --input data/raw/clients.csv \
        --topic clients-realtime \
        --rate 2
"""

import argparse
import csv
import json
import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from google.cloud import pubsub_v1
from google.api_core import retry

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataPublisher:
    """Publish CSV/JSON data to Pub/Sub topic."""

    def __init__(self, project_id: str, topic_name: str):
        self.project_id = project_id
        self.topic_name = topic_name
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, topic_name)
        self.message_count = 0
        self.error_count = 0

    def read_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """Read CSV file and return list of dictionaries."""
        records = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row:  # Skip empty rows
                        records.append(dict(row))
            logger.info(f"✓ Read {len(records)} records from {file_path}")
            return records
        except Exception as e:
            logger.error(f"✗ Error reading CSV: {e}")
            return []

    def read_json_lines(self, file_path: str) -> List[Dict[str, Any]]:
        """Read JSONL file (one JSON per line)."""
        records = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            record = json.loads(line)
                            records.append(record)
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping invalid JSON line: {line[:50]}")
            logger.info(f"✓ Read {len(records)} records from {file_path}")
            return records
        except Exception as e:
            logger.error(f"✗ Error reading JSONL: {e}")
            return []

    def read_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Read JSON file (array of objects or single object)."""
        records = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    records = data
                elif isinstance(data, dict):
                    records = [data]
            logger.info(f"✓ Read {len(records)} records from {file_path}")
            return records
        except Exception as e:
            logger.error(f"✗ Error reading JSON: {e}")
            return []

    def read_records(self, file_path: str) -> List[Dict[str, Any]]:
        """Read records from file (auto-detect format)."""
        path = Path(file_path)

        if path.suffix.lower() == '.csv':
            return self.read_csv(file_path)
        elif path.suffix.lower() == '.json':
            return self.read_json_file(file_path)
        elif path.suffix.lower() == '.jsonl':
            return self.read_json_lines(file_path)
        else:
            logger.error(f"✗ Unsupported file format: {path.suffix}")
            return []

    def publish_message(self, record: Dict[str, Any]) -> bool:
        """Publish single record to Pub/Sub."""
        try:
            # Convert to JSON
            message_json = json.dumps(record, ensure_ascii=False)
            message_bytes = message_json.encode('utf-8')

            # Publish with retry
            future = self.publisher.publish(
                self.topic_path,
                message_bytes,
                timestamp=datetime.now().isoformat(),
            )

            # Wait for message to be published
            message_id = future.result(timeout=5.0)

            self.message_count += 1
            if self.message_count % 100 == 0:
                logger.info(f"  ✓ Published {self.message_count} messages")

            return True

        except Exception as e:
            logger.error(f"✗ Error publishing message: {e}")
            self.error_count += 1
            return False

    def publish_records(self, records: List[Dict[str, Any]], rate: float = 1.0):
        """Publish records with rate limiting."""
        if not records:
            logger.warning("No records to publish")
            return

        interval = 1.0 / rate  # Interval in seconds between messages

        logger.info(f"Publishing {len(records)} messages to topic: {self.topic_name}")
        logger.info(f"Rate: {rate} messages/second (interval: {interval:.3f}s)")
        logger.info("Starting publication...")
        print("")

        start_time = time.time()

        for idx, record in enumerate(records, 1):
            # Publish message
            if not self.publish_message(record):
                logger.warning(f"Failed to publish message {idx}/{len(records)}")

            # Rate limiting (except for last message)
            if idx < len(records):
                time.sleep(interval)

            # Progress every 100 messages
            if idx % 100 == 0 or idx == len(records):
                elapsed = time.time() - start_time
                rate_actual = idx / elapsed if elapsed > 0 else 0
                logger.info(
                    f"Progress: {idx}/{len(records)} ({100*idx/len(records):.1f}%) - "
                    f"Rate: {rate_actual:.1f} msg/s"
                )

        elapsed = time.time() - start_time
        logger.info("")
        logger.info("=" * 70)
        logger.info("PUBLICATION COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Total messages published: {self.message_count}")
        logger.info(f"Failed messages: {self.error_count}")
        logger.info(f"Time elapsed: {elapsed:.2f} seconds")
        logger.info(f"Average rate: {self.message_count / elapsed:.2f} msg/s")
        logger.info("")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Publish data to Google Cloud Pub/Sub for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Publish orders at 5 msg/sec
  python beam/publish_test_data.py \\
    --project ecommerce-494010 \\
    --input data/raw/orders.csv \\
    --topic orders-realtime \\
    --rate 5

  # Publish clients at 2 msg/sec
  python beam/publish_test_data.py \\
    --project ecommerce-494010 \\
    --input data/raw/clients.csv \\
    --topic clients-realtime \\
    --rate 2

  # Publish all data quickly (10 msg/sec)
  python beam/publish_test_data.py \\
    --project ecommerce-494010 \\
    --input data/raw/page_views.csv \\
    --topic pageviews-realtime \\
    --rate 10
        """
    )

    parser.add_argument(
        "--project",
        required=True,
        help="GCP Project ID"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input CSV or JSON file path"
    )
    parser.add_argument(
        "--topic",
        required=True,
        help="Pub/Sub topic name (without project prefix)"
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=1.0,
        help="Publish rate in messages per second (default: 1.0)"
    )

    args = parser.parse_args()

    # Validate inputs
    if not Path(args.input).exists():
        logger.error(f"✗ Input file not found: {args.input}")
        return 1

    if args.rate <= 0:
        logger.error("✗ Rate must be positive")
        return 1

    try:
        # Create publisher
        publisher = DataPublisher(args.project, args.topic)

        # Read records
        logger.info(f"Reading data from: {args.input}")
        records = publisher.read_records(args.input)

        if not records:
            logger.error("✗ No records to publish")
            return 1

        # Publish records
        publisher.publish_records(records, rate=args.rate)

        return 0

    except Exception as e:
        logger.error(f"✗ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
