# ETL vs ELT vs Streaming - Complete Guide for Dataflow

## Understanding the Concepts

### ETL (Extract, Transform, Load)
**Traditional approach:** Data is transformed BEFORE loading into warehouse
- Extract raw data
- **Transform** it (clean, validate, enrich)
- Load into BigQuery
- **When to use:** Batch processing, data quality is critical, complex transformations

### ELT (Extract, Load, Transform)  
**Modern approach:** Data is loaded FIRST, then transformed in warehouse
- Extract raw data
- Load into BigQuery (raw)
- **Transform** using SQL views/queries
- **When to use:** Real-time speed needed, transformation is simple, data volume is huge

### Streaming
**Real-time approach:** Continuous data processing
- Extract from Pub/Sub/Kafka
- Process continuously
- Load immediately
- **When to use:** Real-time dashboards, instant alerts, IoT sensors

---

## Architecture Comparison

```
BATCH ETL (What we're using)
├─ Data source: GCS CSV
├─ Processing: Dataflow (Apache Beam)
├─ Logic: Parse, Validate, Transform
├─ Output: BigQuery (clean table)
└─ Frequency: On-demand or scheduled (daily/hourly)

BATCH ELT (Alternative)
├─ Data source: GCS CSV
├─ Processing: BigQuery (LOAD first)
├─ Loading: Direct to raw table
├─ Logic: SQL transformations
└─ Frequency: On-demand or scheduled

STREAMING ETL (Real-time)
├─ Data source: Pub/Sub (real-time messages)
├─ Processing: Dataflow (continuous)
├─ Logic: Parse, Validate, Transform
├─ Output: BigQuery (streaming inserts)
└─ Frequency: Continuous
```

---

## Comparison Table

| Aspect | Batch ETL | Batch ELT | Streaming |
|--------|-----------|-----------|-----------|
| **Data Source** | GCS, BigQuery Export | GCS, BigQuery Export | Pub/Sub, Kafka |
| **Latency** | 5-60 minutes | 5-60 minutes | Real-time (<1 sec) |
| **Processing** | Dataflow pipeline | BigQuery SQL | Dataflow pipeline |
| **Transformations** | Python/Java code | SQL queries | Python/Java code |
| **Cost** | $0.04/vCPU-hour | BigQuery scan $6.25/TB | $0.04/vCPU-hour |
| **Complexity** | Medium | Low | High |
| **Best For** | Daily/hourly ETL | Analytics queries | Real-time dashboards |
| **Error Handling** | Can retry entire job | Can rerun SQL | Complex stateful logic |
| **Scalability** | Horizontal (workers) | Horizontal (slots) | Horizontal (workers) |

---

## Our Current Implementation: Batch ETL

### Architecture Diagram
```
GCS CSV
   │
   ├─ gsutil cp data → gs://bucket/orders.csv
   │
Dataflow Worker
   │
   ├─ ParseCSV (utf-8 decode, JSON parse)
   ├─ Validate (required fields, data quality)
   ├─ Enrich (timestamps, computed fields)
   ├─ Clean (remove sensitive data)
   │
BigQuery
   ├─ orders_processed (clean, valid records)
   └─ orders_errors (invalid records + error reason)
```

### Pipeline Flow (BATCH ETL)
```python
Input CSV
  ↓
[Read] → Load all records from GCS
  ↓
[Parse] → Convert bytes to dictionaries
  ↓
[Validate] → Check required fields → Split (valid/invalid)
  ↓ (valid branch)
[Enrich] → Add timestamps, computed fields
  ↓
[Clean] → Remove internal fields
  ↓
[Write] → StreamingInserts to BigQuery main table
  ↓ (invalid branch)
[Write] → StreamingInserts to BigQuery error table

RESULT: Clean data ready for analytics
```

---

## Hands-On: Creating Different ETL Pipelines

### Example 1: BATCH ETL (What We Have)
**File:** `beam/dataflow_etl_pipeline.py`
```python
# Read from GCS CSV
lines = p | 'ReadCSV' >> ReadFromText('gs://bucket/data.csv')

# Parse and validate
records = lines | 'Parse' >> ParDo(ParseCSV())
valid, invalid = records | 'Validate' >> ParDo(ValidateRecord()).with_outputs(...)

# Transform
enriched = valid | 'Enrich' >> ParDo(EnrichRecord())

# Load to BigQuery
enriched | 'Write' >> WriteToBigQuery(...)
```

### Example 2: BATCH ELT (SQL-First Approach)
**File:** `beam/dataflow_elt_pipeline.py` (NEW)

Create this alternative that loads raw then transforms:

```python
"""
Batch ELT Pipeline: Load Raw → Transform in BigQuery

This approach:
1. Loads raw CSV directly to BigQuery without transformations
2. BigQuery SQL transforms the data
3. Useful for massive datasets where transformation is expensive

Usage:
    python beam/dataflow_elt_pipeline.py \
      --input gs://bucket/data.csv \
      --raw_table PROJECT:DATASET.orders_raw
"""

import argparse
import logging
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.io import ReadFromText, WriteToBigQuery
import apache_beam as beam
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)
PROJECT_ID = os.getenv("PROJECT_ID")
DATASET = os.getenv("DATASET", "ecommerce_analytics")

def run_elt_pipeline(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='gs://bucket/data.csv')
    parser.add_argument('--raw_table', 
        default=f'{PROJECT_ID}:{DATASET}.orders_raw')
    
    known_args, pipeline_args = parser.parse_known_args(argv)
    
    pipeline_options = PipelineOptions(pipeline_args)
    
    with beam.Pipeline(options=pipeline_options) as p:
        # Read CSV
        lines = p | 'ReadCSV' >> ReadFromText(known_args.input)
        
        # Split into columns (minimal parsing)
        records = (
            lines
            | 'SplitColumns' >> beam.Map(
                lambda line: dict(zip(
                    ['id', 'client_id', 'status', 'total_amount'],
                    line.split(',')
                ))
            )
        )
        
        # Write raw (NO transformation)
        records | 'WriteRaw' >> WriteToBigQuery(
            table=known_args.raw_table,
            create_disposition='CREATE_IF_NEEDED',
            write_disposition='WRITE_APPEND',
        )

if __name__ == '__main__':
    run_elt_pipeline()
```

Then create SQL file for transformations:
```sql
-- CREATE CLEAN TABLE FROM RAW
CREATE OR REPLACE TABLE `PROJECT.DATASET.orders_processed` AS
SELECT
  SAFE.STRING_AGG(id) as id,
  SAFE.STRING_AGG(client_id) as client_id,
  LOWER(TRIM(status)) as status,
  SAFE.FLOAT64(total_amount) as total_amount,
  CURRENT_TIMESTAMP() as processed_timestamp,
  '2.0' as pipeline_version
FROM `PROJECT.DATASET.orders_raw`
WHERE id IS NOT NULL AND client_id IS NOT NULL
GROUP BY id, client_id, status, total_amount;
```

### Example 3: STREAMING ETL (Real-time)
**File:** `beam/dataflow_streaming_pipeline.py` (NEW)

```python
"""
Streaming ETL Pipeline: Pub/Sub → BigQuery (Real-time)

This approach:
1. Consumes messages from Pub/Sub (real-time)
2. Transforms in Dataflow
3. Writes to BigQuery with streaming inserts
4. Latency: < 1 second

Usage:
    python beam/dataflow_streaming_pipeline.py \
      --project PROJECT_ID \
      --runner DataflowRunner \
      --input_topic projects/PROJECT/topics/orders-realtime
"""

import argparse
import json
import logging
from datetime import datetime
import apache_beam as beam
from apache_beam.options.pipeline_options import (
    PipelineOptions,
    StandardOptions,
    StreamingOptions,
)
from apache_beam.io import ReadFromPubSub, WriteToBigQuery
from apache_beam.transforms import DoFn, ParDo, windowed_value
from apache_beam.utils.timestamp import Timestamp
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)
PROJECT_ID = os.getenv("PROJECT_ID")
DATASET = os.getenv("DATASET", "ecommerce_analytics")

class ParsePubSubMessage(beam.DoFn):
    def process(self, element):
        try:
            message = json.loads(element.decode('utf-8'))
            yield message
        except Exception as e:
            logger.warning(f"Parse error: {e}")
            yield None

class ValidateStreamingRecord(beam.DoFn):
    def process(self, element):
        if element is None:
            return
        
        required = ['order_id', 'client_id', 'amount']
        if all(field in element for field in required):
            yield beam.pvalue.TaggedOutput('valid', element)
        else:
            yield beam.pvalue.TaggedOutput('invalid', {
                **element,
                'error': f'Missing fields: {required}',
                'timestamp': datetime.now().isoformat(),
            })

class EnrichStreamingRecord(beam.DoFn):
    def process(self, element):
        element['processed_timestamp'] = datetime.now().isoformat()
        element['environment'] = 'streaming'
        yield element

def run_streaming_pipeline(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_topic', required=True)
    
    known_args, pipeline_args = parser.parse_known_args(argv)
    
    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(StandardOptions).runner = 'DataflowRunner'
    
    # Streaming options
    streaming_options = pipeline_options.view_as(StreamingOptions)
    streaming_options.streaming = True
    streaming_options.enable_streaming_engine = True
    
    with beam.Pipeline(options=pipeline_options) as p:
        # Read from Pub/Sub
        messages = p | 'ReadPubSub' >> ReadFromPubSub(
            topic=known_args.input_topic
        )
        
        # Parse
        records = messages | 'Parse' >> ParDo(ParsePubSubMessage())
        
        # Validate
        valid, invalid = (
            records 
            | 'Validate' >> ParDo(ValidateStreamingRecord())
            .with_outputs('valid', 'invalid', main='valid')
        )
        
        # Enrich
        enriched = valid | 'Enrich' >> ParDo(EnrichStreamingRecord())
        
        # Write to BigQuery
        enriched | 'WriteToBQ' >> WriteToBigQuery(
            table=f'{PROJECT_ID}:{DATASET}.orders_streaming',
            create_disposition='CREATE_IF_NEEDED',
            write_disposition='WRITE_APPEND',
        )
        
        invalid | 'WriteErrors' >> WriteToBigQuery(
            table=f'{PROJECT_ID}:{DATASET}.orders_errors',
            create_disposition='CREATE_IF_NEEDED',
            write_disposition='WRITE_APPEND',
        )

if __name__ == '__main__':
    run_streaming_pipeline()
```

---

## Choosing Your Approach

### Use BATCH ETL if:
- ✅ Data arrives in batches (daily CSV files)
- ✅ Need complex transformations
- ✅ Data quality is critical
- ✅ Cost matters (process only when needed)
- **Example:** Daily e-commerce order processing

### Use BATCH ELT if:
- ✅ Data is already mostly clean
- ✅ Transformations are simple SQL queries
- ✅ Need fast loading speed
- ✅ Have BigQuery expertise
- **Example:** Cloud billing data ETL

### Use STREAMING if:
- ✅ Need real-time dashboards
- ✅ Data arrives continuously
- ✅ < 1 second latency required
- ✅ IoT or events stream
- **Example:** Real-time order status updates

---

## Deployment Commands

### Deploy BATCH ETL (Current)
```bash
bash beam/submit_to_dataflow.sh
```

### Deploy BATCH ELT (If Created)
```bash
python beam/dataflow_elt_pipeline.py \
  --project=PROJECT_ID \
  --runner=DataflowRunner \
  --input gs://bucket/data.csv
```

### Deploy STREAMING (If Created)
```bash
python beam/dataflow_streaming_pipeline.py \
  --project=PROJECT_ID \
  --runner=DataflowRunner \
  --input_topic projects/PROJECT/topics/orders-realtime
```

---

## Monitoring Each Type

### BATCH ETL
```bash
# Monitor job
gcloud dataflow jobs describe JOB_ID --region=REGION

# Completed when state = DONE
# Check output in BigQuery
bq query "SELECT COUNT(*) FROM DATASET.orders_processed"
```

### BATCH ELT
```bash
# Monitor Dataflow loading
gcloud dataflow jobs describe JOB_ID

# Then run SQL transformation
bq query < sql/transform_orders.sql
```

### STREAMING
```bash
# Monitor continuously
watch -n 5 'gcloud dataflow jobs describe JOB_ID --region=REGION'

# Check real-time data in BigQuery
bq query "SELECT * FROM DATASET.orders_streaming ORDER BY processed_timestamp DESC LIMIT 10"
```

---

## Performance & Cost

### BATCH ETL Cost Example
- 1000 CSV files per day
- 100GB total data
- 2 workers × 1 hour = $0.08

### STREAMING Cost Example
- Continuous data stream
- 24/7 operation
- 2 workers × 24 hours × 30 days = $57.60/month

### BATCH ELT Cost Example
- Same as BATCH ETL + BigQuery queries
- Query 100GB = $0.625/query

---

## Summary

| Need | Choose | Pipeline |
|------|--------|----------|
| Daily batch CSV files | BATCH ETL | `dataflow_etl_pipeline.py` |
| Real-time data | STREAMING | `dataflow_streaming_pipeline.py` |
| Simple SQL transforms | BATCH ELT | `dataflow_elt_pipeline.py` |
| Complex transformations | BATCH ETL | `dataflow_etl_pipeline.py` |
| Minimal latency | STREAMING | `dataflow_streaming_pipeline.py` |

All three run on Google Cloud **Dataflow** — choose based on your data characteristics!

