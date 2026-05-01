"""
Apache Beam Dataflow Pipeline for eCommerce Analytics (GCP Cloud-Native)

This pipeline implements the REAL mini-project requirements:
- Ingestion: Cloud Storage + Pub/Sub
- Processing: Dataflow (Apache Beam) with data cleaning & transformation
- Storage: BigQuery (structured analytics)
- Visualization: Looker Studio

Architecture:
1. Cloud Storage → Cloud Functions (trigger)
2. Cloud Functions → Pub/Sub (real-time streaming)
3. Dataflow job reads from Pub/Sub
4. Transforms: clean, join, aggregate data
5. Writes to BigQuery

Usage:
    python beam/dataflow_pipeline_gcp.py \
        --project ecommerce-494010 \
        --region europe-west1 \
        --runner DataflowRunner \
        --temp-location gs://YOUR-BUCKET/temp/

Requirements:
    - GCP Project with Dataflow API enabled
    - Service account with appropriate permissions
    - Pub/Sub topics created
    - BigQuery datasets created
    - Cloud Storage bucket for temporary files

Author: Team
Date: 2026-05-01
"""

import argparse
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

import apache_beam as beam
from apache_beam.options.pipeline_options import (
    PipelineOptions,
    StandardOptions,
    GoogleCloudOptions,
    WorkerOptions,
)
from apache_beam.transforms import DoFn, ParDo, Map, Filter, CombinePerKey
from apache_beam.transforms.combiners import Sum, Count
from apache_beam.io import WriteToBigQuery
from apache_beam.io.gcp.pubsub import ReadFromPubSub
from apache_beam.utils.timestamp import Timestamp

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = "ecommerce-494010"
DATASET_ID = "ecommerce_analytics"
REGION = "europe-west1"

# Pub/Sub topics
ORDERS_TOPIC = f"projects/{PROJECT_ID}/topics/orders-realtime"
CLIENTS_TOPIC = f"projects/{PROJECT_ID}/topics/clients-realtime"
INCIDENTS_TOPIC = f"projects/{PROJECT_ID}/topics/incidents-realtime"
PAGEVIEWS_TOPIC = f"projects/{PROJECT_ID}/topics/pageviews-realtime"

# BigQuery tables
ORDERS_TABLE = f"{PROJECT_ID}:{DATASET_ID}.orders_stream"
ORDERS_CLEAN_TABLE = f"{PROJECT_ID}:{DATASET_ID}.orders_clean"
CLIENTS_TABLE = f"{PROJECT_ID}:{DATASET_ID}.clients_stream"
CLIENTS_CLEAN_TABLE = f"{PROJECT_ID}:{DATASET_ID}.clients_clean"
INCIDENTS_TABLE = f"{PROJECT_ID}:{DATASET_ID}.incidents_stream"
INCIDENTS_CLEAN_TABLE = f"{PROJECT_ID}:{DATASET_ID}.incidents_clean"
PAGEVIEWS_TABLE = f"{PROJECT_ID}:{DATASET_ID}.pageviews_stream"
METRICS_TABLE = f"{PROJECT_ID}:{DATASET_ID}.metrics_daily"
ERRORS_TABLE = f"{PROJECT_ID}:{DATASET_ID}.pipeline_errors"


# ============================================================================
# TRANSFORMS: DATA CLEANING
# ============================================================================

class ParsePubSubMessage(DoFn):
    """Parse Pub/Sub message (UTF-8 JSON)."""

    def process(self, element, *args, **kwargs):
        try:
            # Pub/Sub message is bytes
            decoded = element.decode("utf-8") if isinstance(element, bytes) else element
            message = json.loads(decoded)
            yield beam.pvalue.TaggedOutput("valid", message)
        except Exception as e:
            logger.warning(f"Parse error: {str(e)}")
            yield beam.pvalue.TaggedOutput("invalid", {
                "raw_message": str(element)[:500],
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "source": "pubsub_parse",
            })


class ValidateOrder(DoFn):
    """Validate order record."""

    def process(self, element, *args, **kwargs):
        required = ["order_id", "client_id", "total_amount", "status", "date_commande"]

        if all(field in element for field in required):
            # Validate data types
            try:
                float(element["total_amount"])
                yield beam.pvalue.TaggedOutput("valid", element)
            except (ValueError, TypeError):
                yield beam.pvalue.TaggedOutput("invalid", {
                    **element,
                    "error": "Invalid total_amount (not numeric)",
                    "timestamp": datetime.now().isoformat(),
                })
        else:
            missing = [f for f in required if f not in element]
            yield beam.pvalue.TaggedOutput("invalid", {
                **element,
                "error": f"Missing fields: {', '.join(missing)}",
                "timestamp": datetime.now().isoformat(),
            })


class ValidateClient(DoFn):
    """Validate client record."""

    def process(self, element, *args, **kwargs):
        required = ["client_id", "email", "nom", "prenom"]

        if all(field in element for field in required):
            yield beam.pvalue.TaggedOutput("valid", element)
        else:
            missing = [f for f in required if f not in element]
            yield beam.pvalue.TaggedOutput("invalid", {
                **element,
                "error": f"Missing fields: {', '.join(missing)}",
                "timestamp": datetime.now().isoformat(),
            })


class ValidateIncident(DoFn):
    """Validate incident record."""

    def process(self, element, *args, **kwargs):
        required = ["incident_id", "client_id", "categorie", "date_signalement"]

        if all(field in element for field in required):
            yield beam.pvalue.TaggedOutput("valid", element)
        else:
            missing = [f for f in required if f not in element]
            yield beam.pvalue.TaggedOutput("invalid", {
                **element,
                "error": f"Missing fields: {', '.join(missing)}",
                "timestamp": datetime.now().isoformat(),
            })


class ValidatePageView(DoFn):
    """Validate page view record."""

    def process(self, element, *args, **kwargs):
        required = ["session_id", "client_id", "page", "date_heure"]

        if all(field in element for field in required):
            yield beam.pvalue.TaggedOutput("valid", element)
        else:
            missing = [f for f in required if f not in element]
            yield beam.pvalue.TaggedOutput("invalid", {
                **element,
                "error": f"Missing fields: {', '.join(missing)}",
                "timestamp": datetime.now().isoformat(),
            })


class RemoveDuplicates(DoFn):
    """Remove duplicate records by ID."""

    def __init__(self, id_field: str):
        self.id_field = id_field
        self.seen_ids = set()

    def process(self, element, *args, **kwargs):
        record_id = element.get(self.id_field)
        if record_id and record_id not in self.seen_ids:
            self.seen_ids.add(record_id)
            yield element


class EnrichRecord(DoFn):
    """Add metadata and processing info."""

    def process(self, element, *args, **kwargs):
        element["processing_timestamp"] = datetime.now().isoformat()
        element["pipeline_version"] = "1.0-dataflow"
        element["pipeline_environment"] = "GCP-Dataflow"
        yield element


class FilterNulls(DoFn):
    """Remove records with null/empty critical fields."""

    def process(self, element, *args, **kwargs):
        # Check for null values in critical fields
        critical_fields = [k for k, v in element.items() if k.endswith("_id")]
        has_nulls = any(
            not element.get(field) or element.get(field) == "NULL"
            for field in critical_fields
        )

        if not has_nulls:
            yield element
        else:
            logger.info(f"Filtered null record: {element}")


# ============================================================================
# TRANSFORMS: AGGREGATION & METRICS
# ============================================================================

class CalculateOrderMetrics(DoFn):
    """Calculate daily order metrics."""

    def process(self, element, *args, **kwargs):
        # Extract date from timestamp
        try:
            date_str = element.get("date_commande", "").split("T")[0]
            region = element.get("region", "UNKNOWN")

            yield {
                "date": date_str,
                "region": region,
                "order_id": element.get("order_id"),
                "amount": float(element.get("total_amount", 0)),
            }
        except Exception as e:
            logger.warning(f"Metric calculation error: {e}")


class AggregateDailyMetrics(DoFn):
    """Aggregate metrics per day and region."""

    def process(self, element, *args, **kwargs):
        """Aggregate from (date, [orders]) tuples."""
        date = element[0]
        orders = element[1]

        total_amount = sum(o.get("amount", 0) for o in orders)
        order_count = len(orders)
        unique_regions = set(o.get("region") for o in orders)

        yield {
            "date": date,
            "total_revenue": total_amount,
            "order_count": order_count,
            "avg_order_value": total_amount / order_count if order_count > 0 else 0,
            "unique_regions": len(unique_regions),
            "processing_timestamp": datetime.now().isoformat(),
        }


class IdentifyInactiveClients(DoFn):
    """Identify clients with no recent activity."""

    def process(self, element, *args, **kwargs):
        client_id = element[0]
        orders = list(element[1])

        if len(orders) == 0:
            yield {
                "client_id": client_id,
                "status": "inactive",
                "last_order_date": None,
                "total_orders": 0,
                "total_spent": 0,
                "detection_date": datetime.now().isoformat(),
            }
        else:
            total_spent = sum(float(o.get("total_amount", 0)) for o in orders)
            yield {
                "client_id": client_id,
                "status": "active",
                "last_order_date": max(o.get("date_commande") for o in orders),
                "total_orders": len(orders),
                "total_spent": total_spent,
                "detection_date": datetime.now().isoformat(),
            }


# ============================================================================
# SCHEMAS: BigQuery
# ============================================================================

ORDERS_SCHEMA = {
    "fields": [
        {"name": "order_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "client_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "total_amount", "type": "FLOAT64", "mode": "REQUIRED"},
        {"name": "status", "type": "STRING", "mode": "REQUIRED"},
        {"name": "date_commande", "type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "mode_paiement", "type": "STRING", "mode": "NULLABLE"},
        {"name": "region", "type": "STRING", "mode": "NULLABLE"},
        {"name": "produits", "type": "JSON", "mode": "NULLABLE"},
        {"name": "processing_timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "pipeline_version", "type": "STRING", "mode": "NULLABLE"},
    ]
}

CLIENTS_SCHEMA = {
    "fields": [
        {"name": "client_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "nom", "type": "STRING", "mode": "REQUIRED"},
        {"name": "prenom", "type": "STRING", "mode": "REQUIRED"},
        {"name": "email", "type": "STRING", "mode": "REQUIRED"},
        {"name": "age", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "sexe", "type": "STRING", "mode": "NULLABLE"},
        {"name": "pays", "type": "STRING", "mode": "NULLABLE"},
        {"name": "date_inscription", "type": "DATE", "mode": "NULLABLE"},
        {"name": "processing_timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
    ]
}

INCIDENTS_SCHEMA = {
    "fields": [
        {"name": "incident_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "client_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "date_signalement", "type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "categorie", "type": "STRING", "mode": "REQUIRED"},
        {"name": "description", "type": "STRING", "mode": "NULLABLE"},
        {"name": "statut", "type": "STRING", "mode": "REQUIRED"},
        {"name": "niveau_priorite", "type": "STRING", "mode": "NULLABLE"},
        {"name": "processing_timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
    ]
}

PAGEVIEWS_SCHEMA = {
    "fields": [
        {"name": "session_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "client_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "page", "type": "STRING", "mode": "REQUIRED"},
        {"name": "date_heure", "type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "duree_seconde", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "appareil", "type": "STRING", "mode": "NULLABLE"},
        {"name": "navigateur", "type": "STRING", "mode": "NULLABLE"},
        {"name": "processing_timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
    ]
}

METRICS_SCHEMA = {
    "fields": [
        {"name": "date", "type": "DATE", "mode": "REQUIRED"},
        {"name": "total_revenue", "type": "FLOAT64", "mode": "REQUIRED"},
        {"name": "order_count", "type": "INTEGER", "mode": "REQUIRED"},
        {"name": "avg_order_value", "type": "FLOAT64", "mode": "REQUIRED"},
        {"name": "unique_regions", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "processing_timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
    ]
}

ERRORS_SCHEMA = {
    "fields": [
        {"name": "raw_message", "type": "STRING", "mode": "NULLABLE"},
        {"name": "error", "type": "STRING", "mode": "REQUIRED"},
        {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "source", "type": "STRING", "mode": "REQUIRED"},
    ]
}


# ============================================================================
# PIPELINE
# ============================================================================

def run_pipeline(project_id, region, temp_location):
    """Build and run Dataflow pipeline."""

    logger.info("=" * 80)
    logger.info("APACHE BEAM DATAFLOW PIPELINE (GCP Cloud-Native)")
    logger.info("=" * 80)
    logger.info(f"Project: {project_id}")
    logger.info(f"Region: {region}")
    logger.info(f"Temp Location: {temp_location}")
    logger.info("")

    # Pipeline options for Dataflow
    options = PipelineOptions()

    # Standard options
    options.view_as(StandardOptions).runner = "DataflowRunner"
    options.view_as(StandardOptions).streaming = True

    # Google Cloud options
    google_cloud_options = options.view_as(GoogleCloudOptions)
    google_cloud_options.project = project_id
    google_cloud_options.region = region
    google_cloud_options.temp_location = temp_location
    google_cloud_options.job_name = "ecommerce-analytics-pipeline"

    # Worker options
    worker_options = options.view_as(WorkerOptions)
    worker_options.max_num_workers = 10
    worker_options.machine_type = "n1-standard-2"

    # Build pipeline
    with beam.Pipeline(options=options) as pipeline:

        # ====================================================================
        # ORDERS STREAM
        # ====================================================================
        logger.info("Building ORDERS stream...")
        orders_raw = (
            pipeline
            | "Read Orders from Pub/Sub" >> ReadFromPubSub(topic=ORDERS_TOPIC)
            | "Parse Orders" >> ParDo(ParsePubSubMessage()).with_outputs(
                "valid", "invalid", main="valid"
            )
        )

        orders_valid = orders_raw.valid
        orders_invalid = orders_raw.invalid

        orders_validated = (
            orders_valid
            | "Validate Orders" >> ParDo(ValidateOrder()).with_outputs(
                "valid", "invalid", main="valid"
            )
        )

        orders_clean = (
            orders_validated.valid
            | "Filter Order Nulls" >> ParDo(FilterNulls())
            | "Remove Order Duplicates" >> ParDo(RemoveDuplicates("order_id"))
            | "Enrich Orders" >> ParDo(EnrichRecord())
        )

        # Write orders to BigQuery
        orders_clean | "Write Orders to BQ" >> WriteToBigQuery(
            table=ORDERS_TABLE,
            schema=ORDERS_SCHEMA,
            write_disposition="WRITE_APPEND",
            create_disposition="CREATE_IF_NEEDED",
        )

        # ====================================================================
        # CLIENTS STREAM
        # ====================================================================
        logger.info("Building CLIENTS stream...")
        clients_raw = (
            pipeline
            | "Read Clients from Pub/Sub" >> ReadFromPubSub(topic=CLIENTS_TOPIC)
            | "Parse Clients" >> ParDo(ParsePubSubMessage()).with_outputs(
                "valid", "invalid", main="valid"
            )
        )

        clients_valid = clients_raw.valid
        clients_invalid = clients_raw.invalid

        clients_validated = (
            clients_valid
            | "Validate Clients" >> ParDo(ValidateClient()).with_outputs(
                "valid", "invalid", main="valid"
            )
        )

        clients_clean = (
            clients_validated.valid
            | "Filter Client Nulls" >> ParDo(FilterNulls())
            | "Remove Client Duplicates" >> ParDo(RemoveDuplicates("client_id"))
            | "Enrich Clients" >> ParDo(EnrichRecord())
        )

        # Write clients to BigQuery
        clients_clean | "Write Clients to BQ" >> WriteToBigQuery(
            table=CLIENTS_TABLE,
            schema=CLIENTS_SCHEMA,
            write_disposition="WRITE_APPEND",
            create_disposition="CREATE_IF_NEEDED",
        )

        # ====================================================================
        # INCIDENTS STREAM
        # ====================================================================
        logger.info("Building INCIDENTS stream...")
        incidents_raw = (
            pipeline
            | "Read Incidents from Pub/Sub" >> ReadFromPubSub(topic=INCIDENTS_TOPIC)
            | "Parse Incidents" >> ParDo(ParsePubSubMessage()).with_outputs(
                "valid", "invalid", main="valid"
            )
        )

        incidents_valid = incidents_raw.valid
        incidents_invalid = incidents_raw.invalid

        incidents_validated = (
            incidents_valid
            | "Validate Incidents" >> ParDo(ValidateIncident()).with_outputs(
                "valid", "invalid", main="valid"
            )
        )

        incidents_clean = (
            incidents_validated.valid
            | "Filter Incident Nulls" >> ParDo(FilterNulls())
            | "Remove Incident Duplicates" >> ParDo(RemoveDuplicates("incident_id"))
            | "Enrich Incidents" >> ParDo(EnrichRecord())
        )

        # Write incidents to BigQuery
        incidents_clean | "Write Incidents to BQ" >> WriteToBigQuery(
            table=INCIDENTS_TABLE,
            schema=INCIDENTS_SCHEMA,
            write_disposition="WRITE_APPEND",
            create_disposition="CREATE_IF_NEEDED",
        )

        # ====================================================================
        # PAGEVIEWS STREAM
        # ====================================================================
        logger.info("Building PAGEVIEWS stream...")
        pageviews_raw = (
            pipeline
            | "Read PageViews from Pub/Sub" >> ReadFromPubSub(topic=PAGEVIEWS_TOPIC)
            | "Parse PageViews" >> ParDo(ParsePubSubMessage()).with_outputs(
                "valid", "invalid", main="valid"
            )
        )

        pageviews_valid = pageviews_raw.valid
        pageviews_invalid = pageviews_raw.invalid

        pageviews_validated = (
            pageviews_valid
            | "Validate PageViews" >> ParDo(ValidatePageView()).with_outputs(
                "valid", "invalid", main="valid"
            )
        )

        pageviews_clean = (
            pageviews_validated.valid
            | "Filter PageView Nulls" >> ParDo(FilterNulls())
            | "Enrich PageViews" >> ParDo(EnrichRecord())
        )

        # Write pageviews to BigQuery
        pageviews_clean | "Write PageViews to BQ" >> WriteToBigQuery(
            table=PAGEVIEWS_TABLE,
            schema=PAGEVIEWS_SCHEMA,
            write_disposition="WRITE_APPEND",
            create_disposition="CREATE_IF_NEEDED",
        )

        # ====================================================================
        # ERROR HANDLING: Collect all errors
        # ====================================================================
        logger.info("Setting up ERROR stream...")
        all_errors = (
            [
                orders_invalid,
                orders_validated.invalid,
                clients_invalid,
                clients_validated.invalid,
                incidents_invalid,
                incidents_validated.invalid,
                pageviews_invalid,
                pageviews_validated.invalid,
            ]
            | "Flatten Errors" >> beam.Flatten()
        )

        # Write errors to BigQuery
        all_errors | "Write Errors to BQ" >> WriteToBigQuery(
            table=ERRORS_TABLE,
            schema=ERRORS_SCHEMA,
            write_disposition="WRITE_APPEND",
            create_disposition="CREATE_IF_NEEDED",
        )

    logger.info("")
    logger.info("=" * 80)
    logger.info("✓ Dataflow pipeline submitted successfully")
    logger.info("  Monitor at: https://console.cloud.google.com/dataflow")
    logger.info("=" * 80)


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Apache Beam Dataflow Pipeline for eCommerce Analytics (GCP)"
    )
    parser.add_argument(
        "--project",
        default=PROJECT_ID,
        help=f"GCP Project ID (default: {PROJECT_ID})",
    )
    parser.add_argument(
        "--region",
        default=REGION,
        help=f"GCP region (default: {REGION})",
    )
    parser.add_argument(
        "--temp-location",
        required=True,
        help="GCS path for temporary files (gs://bucket/temp/)",
    )

    args = parser.parse_args()

    try:
        run_pipeline(args.project, args.region, args.temp_location)
        return 0
    except Exception as e:
        logger.error(f"✗ Pipeline failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
