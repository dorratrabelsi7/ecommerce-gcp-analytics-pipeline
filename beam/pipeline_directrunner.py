"""
Apache Beam pipeline: Local CSV/JSON to Text Output (DirectRunner)

This pipeline runs LOCALLY without GCP connectivity:
1. Reads from local CSV/JSON files (data/ directory)
2. Parses and validates JSON/CSV payloads
3. Enriches with processing timestamp
4. Writes valid messages to local text files
5. Writes invalid messages to error file

IMPORTANT: This is for LOCAL TESTING ONLY with DirectRunner.
For production, use dataflow_etl_pipeline.py with DataflowRunner on GCP.

Usage:
    python beam/pipeline_directrunner.py --input data/raw/orders.csv --limit 100
    python beam/pipeline_directrunner.py --input data/raw/orders.json
    python beam/pipeline_directrunner.py --all  # Process all CSV files
"""

import sys
import argparse
import json
import logging
import csv
import os
from datetime import datetime
from pathlib import Path

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.transforms import DoFn, ParDo, Map
from apache_beam.io import ReadFromText, WriteToText

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATA_DIR = "data/raw"
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================================
# READ SOURCES
# ============================================================================

class ReadCSV(beam.PTransform):
    """Read CSV file and convert to dictionaries."""
    
    def __init__(self, file_path, delimiter=","):
        self.file_path = file_path
        self.delimiter = delimiter
    
    def expand(self, pcoll):
        return (
            pcoll
            | "Read file" >> ReadFromText(self.file_path, skip_header_lines=1)
            | "Parse CSV" >> beam.ParDo(self._parse_csv)
        )
    
    def _parse_csv(self, line):
        """Parse CSV line based on file type."""
        try:
            # Detect file type and parse accordingly
            if "client" in self.file_path:
                fields = ["client_id", "nom", "prenom", "email", "age", "sexe", "pays", "date_inscription"]
            elif "incident" in self.file_path:
                fields = ["incident_id", "client_id", "date_signalement", "categorie", "description", "statut", "niveau_priorite"]
            elif "order" in self.file_path:
                fields = ["order_id", "client_id", "date_commande", "total_amount", "status", "mode_paiement"]
            elif "page_view" in self.file_path:
                fields = ["session_id", "client_id", "page", "date_heure", "duree_seconde", "appareil", "navigateur"]
            else:
                fields = line.split(self.delimiter)
            
            values = line.split(self.delimiter)
            record = dict(zip(fields, values))
            yield record
        except Exception as e:
            logger.warning(f"CSV parse error: {str(e)}")


class ReadJSON(beam.PTransform):
    """Read JSONL file (one JSON per line)."""
    
    def __init__(self, file_path):
        self.file_path = file_path
    
    def expand(self, pcoll):
        return (
            pcoll
            | "Read file" >> ReadFromText(self.file_path)
            | "Parse JSON" >> beam.ParDo(self._parse_json)
        )
    
    def _parse_json(self, line):
        try:
            if line.strip():
                record = json.loads(line)
                yield record
        except Exception as e:
            logger.warning(f"JSON parse error: {str(e)}")


# ============================================================================
# BEAM TRANSFORMS
# ============================================================================

class ValidateRecord(beam.DoFn):
    """Validate required fields based on source."""
    
    def process(self, element):
        # Identify source type and validate accordingly
        if "order_id" in element:
            required = ["order_id", "client_id", "total_amount", "status"]
        elif "client_id" in element and "incident_id" in element:
            required = ["incident_id", "client_id"]
        elif "session_id" in element:
            required = ["session_id", "client_id", "page"]
        else:
            required = ["client_id"]
        
        if all(field in element for field in required):
            yield beam.pvalue.TaggedOutput("valid", element)
        else:
            missing = [f for f in required if f not in element]
            yield beam.pvalue.TaggedOutput("invalid", {
                **element,
                "error": f"Missing fields: {', '.join(missing)}",
                "timestamp": datetime.now().isoformat(),
            })


class EnrichRecord(beam.DoFn):
    """Add processing metadata."""
    
    def process(self, element):
        element["processing_timestamp"] = datetime.now().isoformat()
        element["pipeline_version"] = "1.0-directrunner"
        element["source"] = "local-batch"
        yield element


class FormatOutput(beam.DoFn):
    """Format record as JSON string for output."""
    
    def process(self, element):
        yield json.dumps(element, ensure_ascii=False, indent=2)


# ============================================================================
# PIPELINE
# ============================================================================

def run_pipeline(input_file, limit, all_files):
    """Build and run Beam pipeline locally."""
    
    logger.info("=" * 80)
    logger.info("APACHE BEAM PIPELINE (DIRECTRUNNER - LOCAL)")
    logger.info("=" * 80)
    
    # Prepare input files
    input_files = []
    
    if all_files:
        input_files = list(Path(DATA_DIR).glob("*.csv")) + list(Path(DATA_DIR).glob("*.json"))
        logger.info(f"Processing ALL files: {len(input_files)} files found")
    elif input_file:
        if not os.path.exists(input_file):
            logger.error(f"File not found: {input_file}")
            return 1
        input_files = [input_file]
    else:
        logger.error("Specify --input FILE or --all")
        return 1
    
    # Pipeline options - DirectRunner only
    options = PipelineOptions()
    options.view_as(StandardOptions).runner = "DirectRunner"
    options.view_as(StandardOptions).streaming = False
    
    # Build pipeline
    with beam.Pipeline(options=options) as pipeline:
        all_valid_records = []
        all_invalid_records = []
        
        for input_path in input_files:
            logger.info(f"Processing: {input_path}")
            file_name = Path(input_path).stem
            
            # Read based on file type
            if input_path.endswith('.csv'):
                records = (
                    pipeline
                    | f"Read {file_name}" >> beam.Create([''])
                    | f"Load CSV {file_name}" >> ReadCSV(input_path)
                )
            elif input_path.endswith('.json'):
                records = (
                    pipeline
                    | f"Read {file_name}" >> ReadFromText(input_path)
                    | f"Parse JSON {file_name}" >> beam.ParDo(
                        lambda line: [json.loads(line)] if line.strip() else []
                    )
                )
            else:
                continue
            
            # Apply limit
            if limit:
                records = records | f"Limit {file_name}" >> beam.transforms.combiners.Top.Largest(limit)
            
            # Validate
            validated = (
                records
                | f"Validate {file_name}" >> ParDo(ValidateRecord()).with_outputs(
                    "valid", "invalid", main="valid"
                )
            )
            
            # Enrich valid records
            enriched = (
                validated.valid
                | f"Enrich {file_name}" >> ParDo(EnrichRecord())
                | f"Format valid {file_name}" >> ParDo(FormatOutput())
            )
            
            # Write valid records
            enriched | f"Write valid {file_name}" >> WriteToText(
                f"{OUTPUT_DIR}/valid_{file_name}",
                file_name_suffix=".jsonl"
            )
            
            # Format and write invalid records
            (
                validated.invalid
                | f"Format invalid {file_name}" >> ParDo(FormatOutput())
                | f"Write invalid {file_name}" >> WriteToText(
                    f"{OUTPUT_DIR}/invalid_{file_name}",
                    file_name_suffix=".jsonl"
                )
            )
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("✓ Pipeline execution complete")
    logger.info(f"✓ Output files written to: {OUTPUT_DIR}/")
    logger.info("=" * 80)
    return 0


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Apache Beam pipeline (DirectRunner - Local Testing)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python beam/pipeline_directrunner.py --input data/raw/orders.csv
  python beam/pipeline_directrunner.py --all
  python beam/pipeline_directrunner.py --input data/raw/clients.csv --limit 50
        """
    )
    parser.add_argument(
        "--input",
        help="Input CSV or JSON file path"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all CSV/JSON files in data/raw/"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max records to process per file"
    )
    
    args = parser.parse_args()
    
    try:
        return run_pipeline(args.input, args.limit, args.all)
    except Exception as e:
        logger.error(f"✗ Pipeline failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
