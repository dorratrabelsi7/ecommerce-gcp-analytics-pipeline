"""
Apache Beam pipeline: ETL on Dataflow (Production-Ready)

This pipeline:
1. Reads CSV from Google Cloud Storage
2. Parses and validates records
3. Enriches data with computed fields
4. Writes valid records to BigQuery main table
5. Writes invalid records to error table

Runs on Google Cloud Dataflow (managed service)

Usage:
    python beam/dataflow_etl_pipeline.py \
      --project my-project \
      --region europe-west1 \
      --runner DataflowRunner \
      --staging_location gs://bucket/staging \
      --temp_location gs://bucket/temp
"""

import argparse
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

import apache_beam as beam
from apache_beam.options.pipeline_options import (
    PipelineOptions,
    StandardOptions,
    WorkerOptions,
    SetupOptions,
)
from apache_beam.io import ReadFromText, WriteToBigQuery
from apache_beam.transforms import DoFn, ParDo, Map, PTransform
from apache_beam.utils.timestamp import Timestamp
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = os.getenv("PROJECT_ID", "")
DATASET = os.getenv("DATASET", "ecommerce_analytics")


# ============================================================================
# BEAM TRANSFORMS (ETL LOGIC)
# ============================================================================

class ParseCSVLine(beam.DoFn):
    """Parse CSV line into dictionary."""
    
    def __init__(self, headers):
        super().__init__()
        self.headers = headers
    
    def process(self, line):
        """
        Parse CSV line.
        
        Args:
            line: CSV line as string
            
        Yields:
            Dictionary or None on error
        """
        try:
            # Skip empty lines
            if not line or not line.strip():
                return
            
            # Split by comma
            values = line.split(",")
            
            # Validate column count
            if len(values) != len(self.headers):
                logger.warning(
                    f"Column mismatch: expected {len(self.headers)}, "
                    f"got {len(values)} in line: {line[:100]}"
                )
                yield None
                return
            
            # Create dictionary
            record = dict(zip(self.headers, values))
            yield record
            
        except Exception as e:
            logger.error(f"Parse error in line '{line[:100]}': {str(e)}")
            yield None


class ValidateRecord(beam.DoFn):
    """Validate data quality and required fields."""
    
    def __init__(self, required_fields: list = None):
        super().__init__()
        self.required_fields = required_fields or ["id", "client_id"]
    
    def process(self, element):
        """
        Validate record.
        
        Yields:
            TaggedOutput: 'valid' or 'invalid'
        """
        if element is None:
            return
        
        # Check required fields
        missing_fields = [f for f in self.required_fields if f not in element]
        
        if missing_fields:
            logger.warning(f"Record missing fields: {missing_fields}")
            yield beam.pvalue.TaggedOutput("invalid", {
                **element,
                "validation_error": f"Missing fields: {missing_fields}",
                "error_timestamp": datetime.now().isoformat(),
                "error_stage": "validation",
            })
            return
        
        # Check for empty required fields
        empty_fields = [f for f in self.required_fields if not element.get(f, "").strip()]
        
        if empty_fields:
            logger.warning(f"Record has empty fields: {empty_fields}")
            yield beam.pvalue.TaggedOutput("invalid", {
                **element,
                "validation_error": f"Empty fields: {empty_fields}",
                "error_timestamp": datetime.now().isoformat(),
                "error_stage": "validation",
            })
            return
        
        # Valid record
        yield beam.pvalue.TaggedOutput("valid", element)


class EnrichRecord(beam.DoFn):
    """Add computed fields and metadata."""
    
    def process(self, element):
        """
        Enrich record with computed fields.
        
        Yields:
            Enriched record
        """
        try:
            # Add processing metadata
            element["processed_timestamp"] = datetime.now().isoformat()
            element["pipeline_version"] = "2.0"
            element["execution_environment"] = "dataflow"
            
            # Add computed fields based on total_amount
            if "total_amount" in element:
                try:
                    amount = float(element["total_amount"])
                    element["total_amount_numeric"] = amount
                    element["amount_category"] = (
                        "premium" if amount > 500 
                        else "standard" if amount > 100 
                        else "basic"
                    )
                except ValueError:
                    element["total_amount_numeric"] = 0.0
                    element["amount_category"] = "unknown"
                    logger.warning(f"Invalid amount: {element.get('total_amount')}")
            
            # Parse status
            if "status" in element:
                element["status_normalized"] = element["status"].lower().strip()
            
            yield element
            
        except Exception as e:
            logger.error(f"Enrichment error: {e}")
            yield element


class CleanRecord(beam.DoFn):
    """Remove or transform sensitive fields."""
    
    def process(self, element):
        """
        Clean sensitive data.
        
        Yields:
            Cleaned record
        """
        try:
            # Remove internal fields
            sensitive_fields = ["internal_id", "debug_info"]
            for field in sensitive_fields:
                element.pop(field, None)
            
            # Trim whitespace
            for key in element:
                if isinstance(element[key], str):
                    element[key] = element[key].strip()
            
            yield element
            
        except Exception as e:
            logger.error(f"Cleaning error: {e}")
            yield element


# ============================================================================
# PIPELINE DEFINITION
# ============================================================================

def run_pipeline(argv=None):
    """Main pipeline execution."""
    
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input',
        dest='input',
        default='gs://your-bucket/data/orders.csv',
        help='Input GCS path (CSV file)'
    )
    parser.add_argument(
        '--output_table',
        dest='output_table',
        required=False,
        help='Output BigQuery table (default: PROJECT:DATASET.orders_processed)'
    )
    parser.add_argument(
        '--error_table',
        dest='error_table',
        required=False,
        help='Error BigQuery table (default: PROJECT:DATASET.orders_errors)'
    )
    parser.add_argument(
        '--limit_rows',
        dest='limit_rows',
        type=int,
        default=0,
        help='Limit to N rows (0 = no limit)'
    )
    
    known_args, pipeline_args = parser.parse_known_args(argv)
    
    # Set defaults
    output_table = known_args.output_table or f'{PROJECT_ID}:{DATASET}.orders_processed'
    error_table = known_args.error_table or f'{PROJECT_ID}:{DATASET}.orders_errors'
    
    logger.info(f"Pipeline Configuration:")
    logger.info(f"  Input: {known_args.input}")
    logger.info(f"  Output: {output_table}")
    logger.info(f"  Errors: {error_table}")
    logger.info(f"  Limit: {known_args.limit_rows if known_args.limit_rows > 0 else 'No limit'}")
    
    # Create pipeline options
    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(StandardOptions).runner = 'DataflowRunner'
    pipeline_options.view_as(SetupOptions).save_main_session = True
    
    # Worker configuration
    pipeline_options.view_as(WorkerOptions).num_workers = 2
    pipeline_options.view_as(WorkerOptions).machine_type = 'n1-standard-2'
    
    # Create and run pipeline
    with beam.Pipeline(options=pipeline_options) as p:
        
        # Read CSV from GCS
        raw_lines = p | 'ReadCSV' >> ReadFromText(known_args.input)
        
        # Skip header (first line)
        data_lines = raw_lines | 'SkipHeader' >> beam.Filter(
            lambda x: not x.startswith('id,')
        )
        
        # Limit rows if specified
        if known_args.limit_rows > 0:
            data_lines = (
                data_lines 
                | 'LimitRows' >> beam.combiners.Top.Of(known_args.limit_rows)
            )
        
        # Parse CSV
        records = (
            data_lines
            | 'ParseCSV' >> ParDo(
                ParseCSVLine([
                    'id', 'client_id', 'status', 'total_amount',
                    'order_date', 'created_at'
                ])
            )
        )
        
        # Validate records
        valid, invalid_validation = (
            records
            | 'Validate' >> ParDo(ValidateRecord()).with_outputs(
                'valid', 'invalid', main='valid'
            )
        )
        
        # Enrich valid records
        enriched = (
            valid
            | 'Enrich' >> ParDo(EnrichRecord())
        )
        
        # Clean records
        cleaned = (
            enriched
            | 'Clean' >> ParDo(CleanRecord())
        )
        
        # Write valid records to BigQuery
        (
            cleaned
            | 'WriteToBigQuery' >> WriteToBigQuery(
                table=output_table,
                create_disposition='CREATE_IF_NEEDED',
                write_disposition='WRITE_APPEND',
                schema=None,  # Auto-detect schema
                method='STREAMING_INSERTS',
            )
        )
        
        # Write invalid records to error table
        (
            invalid_validation
            | 'WriteErrors' >> WriteToBigQuery(
                table=error_table,
                create_disposition='CREATE_IF_NEEDED',
                write_disposition='WRITE_APPEND',
                schema=None,
            )
        )
        
        logger.info("Pipeline graph created")


if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("Starting Apache Beam ETL Pipeline for Dataflow")
    logger.info("=" * 70)
    
    try:
        run_pipeline()
        logger.info("=" * 70)
        logger.info("Pipeline completed successfully")
        logger.info("=" * 70)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        raise
