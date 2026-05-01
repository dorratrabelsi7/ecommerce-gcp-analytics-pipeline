"""
Apache Beam pipeline: Pub/Sub to BigQuery (DataflowRunner ONLY)

⚠️  WARNING: This pipeline only works with DataflowRunner on GCP!
    - ReadFromPubSub is NOT compatible with DirectRunner
    - WriteToBigQuery is NOT compatible with DirectRunner
    - Use beam/pipeline_directrunner.py for LOCAL testing with DirectRunner

This pipeline:
1. Pulls messages from Pub/Sub (batch pull, not streaming)
2. Parses and validates JSON payloads
3. Enriches with processing timestamp
4. Writes valid messages to BigQuery
5. Writes invalid messages to error table

Author: Dorra Trabelsi
Date: 2026-04-21

IMPORTANT:
- DirectRunner ❌ NOT SUPPORTED (will fail)
- DataflowRunner ✅ REQUIRED (must run on GCP)
- Cost: Billed per vCPU-hour on Dataflow

Usage (GCP only):
    python beam/pipeline.py --project ecommerce-494010 --runner DataflowRunner
    bash beam/submit_to_dataflow.sh

For LOCAL testing, use:
    python beam/pipeline_directrunner.py --all

See beam/DIRECTRUNNER_GUIDE.md for more details.
"""

import sys
import argparse
import json
import logging
from datetime import datetime

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.io import ReadFromPubSub, WriteToBigQuery
from apache_beam.transforms import DoFn, ParDo, Map
from google.cloud import pubsub_v1
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
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "orders-realtime")
SUBSCRIPTION = f"projects/{PROJECT_ID}/subscriptions/orders-sub"


# ============================================================================
# BEAM TRANSFORMS
# ============================================================================

class ParseJSON(beam.DoFn):
    """Parse UTF-8 encoded JSON message."""
    
    def process(self, element):
        try:
            decoded = element.decode("utf-8")
            message = json.loads(decoded)
            yield beam.pvalue.TaggedOutput("valid", message)
        except Exception as e:
            logger.warning(f"Parse error: {str(e)}")
            yield beam.pvalue.TaggedOutput("invalid", {
                "raw_message": str(element)[:200],
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            })


class ValidateMessage(beam.DoFn):
    """Validate required fields."""
    
    def process(self, element):
        required_fields = ["order_id", "client_id", "total_amount", "status"]
        
        if all(field in element for field in required_fields):
            yield beam.pvalue.TaggedOutput("valid", element)
        else:
            missing = [f for f in required_fields if f not in element]
            yield beam.pvalue.TaggedOutput("invalid", {
                **element,
                "error": f"Missing fields: {', '.join(missing)}",
                "timestamp": datetime.now().isoformat(),
            })


class EnrichMessage(beam.DoFn):
    """Add processing timestamp."""
    
    def process(self, element):
        element["processing_timestamp"] = datetime.now().isoformat()
        element["pipeline_version"] = "1.0"
        yield element


# ============================================================================
# PIPELINE
# ============================================================================

def run_pipeline(project_id, dataset, subscription, limit):
    """Build and run Beam pipeline."""
    
    logger.info("=" * 80)
    logger.info("APACHE BEAM PIPELINE (DIRECTRUNNER)")
    logger.info("=" * 80)
    logger.info(f"Project: {project_id}")
    logger.info(f"Dataset: {dataset}")
    logger.info(f"Subscription: {subscription}")
    logger.info(f"Limit: {limit} messages")
    logger.info("")
    
    # Pipeline options - DirectRunner only
    options = PipelineOptions()
    options.view_as(StandardOptions).runner = "DirectRunner"
    options.view_as(StandardOptions).streaming = False
    
    # Build pipeline
    with beam.Pipeline(options=options) as pipeline:
        
        # Read from Pub/Sub (batch pull)
        logger.info("Reading from Pub/Sub...")
        messages = (
            pipeline
            | "Read from Pub/Sub" >> beam.io.gcp.pubsub.ReadFromPubSub(
                subscription=subscription,
                with_attributes=False,
                timestamp_attribute=None,
            )
            | "Limit messages" >> beam.transforms.combiners.Top.Largest(limit)
            | "Flatten" >> beam.FlatMap(lambda x: x)
        )
        
        # Parse JSON
        parsed = (
            messages
            | "Parse JSON" >> ParDo(ParseJSON()).with_outputs(
                "valid", "invalid", main="valid"
            )
        )
        
        valid_messages = parsed.valid
        invalid_messages = parsed.invalid
        
        # Validate
        validated = (
            valid_messages
            | "Validate" >> ParDo(ValidateMessage()).with_outputs(
                "valid", "invalid", main="valid"
            )
        )
        
        valid_data = validated.valid
        invalid_data = beam.Flatten([validated.invalid, invalid_messages])
        
        # Enrich valid messages
        enriched = (
            valid_data
            | "Enrich" >> ParDo(EnrichMessage())
        )
        
        # Write to BigQuery
        enriched | "Write valid to BQ" >> WriteToBigQuery(
            table=f"{project_id}:{dataset}.orders_stream",
            schema={
                "fields": [
                    {"name": "order_id", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "client_id", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "total_amount", "type": "FLOAT64", "mode": "REQUIRED"},
                    {"name": "status", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "processing_timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
                    {"name": "pipeline_version", "type": "STRING", "mode": "NULLABLE"},
                    {"name": "sent_at", "type": "TIMESTAMP", "mode": "NULLABLE"},
                ]
            },
            write_disposition="WRITE_APPEND",
            create_disposition="CREATE_IF_NEEDED",
        )
        
        # Write to errors table
        invalid_data | "Write invalid to BQ" >> WriteToBigQuery(
            table=f"{project_id}:{dataset}.pipeline_errors",
            schema={
                "fields": [
                    {"name": "raw_message", "type": "STRING", "mode": "NULLABLE"},
                    {"name": "error", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
                ]
            },
            write_disposition="WRITE_APPEND",
            create_disposition="CREATE_IF_NEEDED",
        )
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("✓ Pipeline execution complete")
    logger.info("=" * 80)


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Apache Beam pipeline")
    parser.add_argument(
        "--project",
        default=PROJECT_ID,
        help=f"GCP project ID (default: {PROJECT_ID})"
    )
    parser.add_argument(
        "--dataset",
        default=DATASET,
        help=f"BigQuery dataset (default: {DATASET})"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max messages to process (default: 100)"
    )
    
    args = parser.parse_args()
    
    try:
        run_pipeline(args.project, args.dataset, SUBSCRIPTION, args.limit)
        return 0
    except Exception as e:
        logger.error(f"✗ Pipeline failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
