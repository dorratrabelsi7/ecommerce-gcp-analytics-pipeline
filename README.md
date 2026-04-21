# Cloud-Native E-commerce Analytics Pipeline on GCP

![Python 3.11](https://img.shields.io/badge/python-3.11+-blue)
![GCP Free Tier](https://img.shields.io/badge/GCP-Free%20Tier-success)
![BigQuery](https://img.shields.io/badge/BigQuery-Analytics-orange)
![Apache Beam DirectRunner](https://img.shields.io/badge/Apache%20Beam-DirectRunner-red)

## Project Description

A production-ready, cost-optimized BI pipeline for e-commerce analytics on Google Cloud Platform (GCP). Built entirely within the **GCP Free Tier** with $0 cloud costs.

**Technology Stack:**
- Synthetic data generation: Faker + Pandas + NumPy
- Cloud storage: Google Cloud Storage (GCS)
- Real-time ingestion: Google Pub/Sub
- Processing: Apache Beam (DirectRunner)
- Analytics database: BigQuery
- Visualization: Looker Studio
- Orchestration: Cloud Scheduler + Cloud Functions
- Monitoring: Cloud Logging (cost-free)

## Prerequisites

- Python 3.11+
- GCP account with free tier eligible
- `gcloud` CLI installed and authenticated
- Git
- ~500 MB disk space for development data

## Quick Setup (5 commands)

```bash
# 1. Clone and setup environment
git clone https://github.com/dorratrabelsi7/ecommerce-gcp-analytics-pipeline.git
cd ecommerce-gcp-analytics-pipeline
cp .env.example .env
# Edit .env with your GCP project ID

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate synthetic data
python scripts/generate_data.py

# 4. Clean data
python scripts/prepare_data.py

# 5. Setup GCP infrastructure (preview first)
bash deploy/setup_gcp.sh --dry-run
# Then run without --dry-run to create resources
bash deploy/setup_gcp.sh
```

## Execution Order

```bash
1. python scripts/generate_data.py           # Generate 70k synthetic rows
2. python scripts/prepare_data.py            # Clean and validate
3. bash deploy/setup_gcp.sh                  # Setup GCP infrastructure
4. python scripts/load_to_bq.py              # Load to BigQuery
5. bash deploy/deploy_function.sh            # Deploy Cloud Function
6. python scripts/simulate_realtime.py --limit 200   # Start stream simulator
7. python beam/pipeline.py --limit 100       # Run Beam pipeline
8. bash deploy/setup_scheduler.sh            # Configure schedulers
9. python monitoring/setup_alerts.py         # Setup monitoring
10. python monitoring/health_check.py        # Check pipeline health
```

## GCP Free Tier Limits Reference

| Service | Free Limit | This Project Uses | Safe? |
|---------|-----------|-------------------|-------|
| BigQuery Storage | 10 GB/month | ~50 MB | ✅ |
| BigQuery Queries | 1 TB/month | ~100 MB | ✅ |
| Cloud Storage | 5 GB/month | ~20 MB | ✅ |
| Cloud Functions | 2M invocations/month | < 100 | ✅ |
| Pub/Sub | 10 GB/month | ~50 KB | ✅ |
| Cloud Scheduler | 3 jobs/month | 3 | ✅ |
| Looker Studio | Always free | Yes | ✅ |
| DirectRunner | Always free (local) | Yes | ✅ |

**CRITICAL: Do NOT enable Dataflow, Compute Engine, or Cloud Run** — these are not part of the free tier.

## Project Structure

```
ecommerce-gcp-analytics-pipeline/
├── data/                          # Data storage
│   ├── raw/                       # Generated synthetic data
│   └── clean/                     # Cleaned and validated data
├── scripts/                       # Python scripts
│   ├── generate_data.py           # Data generation with Faker
│   ├── prepare_data.py            # Data cleaning and validation
│   ├── load_to_bq.py              # Load CSV to BigQuery
│   └── simulate_realtime.py       # Real-time event simulator
├── sql/                           # BigQuery SQL files
│   ├── 01_create_tables.sql       # Table schemas
│   ├── 02_create_views.sql        # Analytical views
│   ├── 03_advanced_analytics.sql  # Advanced queries
│   └── 04_scheduled_queries.sql   # Scheduled query definitions
├── functions/                     # Cloud Functions
│   └── process_upload/
│       ├── main.py                # GCS trigger handler
│       └── requirements.txt       # Function dependencies
├── beam/                          # Apache Beam pipeline
│   ├── pipeline.py                # DirectRunner pipeline
│   └── run_pipeline.sh            # Pipeline runner script
├── monitoring/                    # Monitoring and health checks
│   ├── health_check.py            # Pipeline health verification
│   ├── setup_alerts.py            # Log-based alert configuration
│   └── dashboards.sql             # Monitoring queries
├── deploy/                        # Deployment scripts
│   ├── setup_gcp.sh               # GCP infrastructure setup
│   ├── setup_scheduler.sh         # Cloud Scheduler setup
│   └── deploy_function.sh         # Cloud Function deployment
├── docs/                          # Documentation
│   ├── architecture.md            # System design
│   ├── sql_explained.md           # SQL queries explained
│   ├── data_generation_report.txt # Generation statistics
│   └── cleaning_report.txt        # Data quality report
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment template
├── .gitignore                     # Git ignore rules
└── README.md                      # This file
```

## Documentation

- **[Architecture](docs/architecture.md)** — System design, data flow, and cost breakdown
- **[SQL Guide](docs/sql_explained.md)** — Every query explained in French
- **[Data Generation](docs/data_generation_report.txt)** — Statistics from synthetic data generation
- **[Data Cleaning](docs/cleaning_report.txt)** — Data quality metrics

## Key Features

✅ **Cost-Free:** All resources use GCP Free Tier — $0 cloud costs  
✅ **Scalable:** DirectRunner handles 100k+ messages locally  
✅ **Production-Ready:** Structured logging, error handling, monitoring  
✅ **Well-Documented:** French and English documentation  
✅ **Modular:** Each component can run independently  
✅ **Git-Driven:** Every step tracked with conventional commits  

## How to Run Each Component

### Generate Data
```bash
python scripts/generate_data.py
# Outputs: clients.csv, products.csv, orders.csv, order_items.csv, 
#          incidents.csv, page_views.csv to data/raw/
```

### Clean Data
```bash
python scripts/prepare_data.py
# Outputs: *_clean.csv files to data/clean/
# Creates: docs/cleaning_report.txt
```

### Load to BigQuery
```bash
# First, setup GCP:
bash deploy/setup_gcp.sh

# Then load:
python scripts/load_to_bq.py
```

### Real-time Stream
```bash
# Simulate 200 orders (default)
python scripts/simulate_realtime.py

# Custom: simulate 500 orders with 1 second delay
python scripts/simulate_realtime.py --limit 500 --speed 1.0

# Verbose output:
python scripts/simulate_realtime.py --verbose
```

### Run Beam Pipeline
```bash
# Process 100 messages from Pub/Sub (DirectRunner — local only)
python beam/pipeline.py --limit 100

# Custom:
python beam/pipeline.py --project ecommerce-494010 --limit 500
```

### Health Check
```bash
python monitoring/health_check.py
# Displays: table row counts, Pub/Sub backlog, error logs
```

## Cost Management Tips

1. **Always use `--dry-run` first:**
   ```bash
   bash deploy/setup_gcp.sh --dry-run
   ```

2. **Monitor query costs in BigQuery:**
   - Use `LIMIT 1000` on exploratory queries
   - Use partition filters in `WHERE` clauses
   - Check estimated bytes scanned before executing

3. **Check GCP billing:**
   ```bash
   gcloud billing accounts list
   ```

4. **Set up budget alerts** in GCP Console (optional)

## Troubleshooting

### `gcloud: command not found`
Install the GCP SDK: https://cloud.google.com/sdk/docs/install

### `GOOGLE_APPLICATION_CREDENTIALS not found`
1. Create a service account key in GCP Console
2. Download JSON file
3. Set in `.env`: `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`

### Pub/Sub messages not showing
Check subscription backlog:
```bash
gcloud pubsub subscriptions describe orders-sub
```

### BigQuery queries timing out
Add partition filter to `WHERE` clause:
```sql
WHERE DATE(order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
```

## Git Commit Convention

Every completed step follows this format:

```
type(scope): short description

type: feat|fix|data|sql|infra|docs|chore
scope: generation, cleaning, gcp, bigquery, beam, pubsub, functions, scheduler, monitoring, etc.
```

Examples:
- `data(generation): generate 70k synthetic rows with Faker`
- `infra(gcp): set up GCS buckets and BigQuery dataset`
- `sql(bigquery): create 7 analytical views with window functions`

## Author & Contact

- **Author:** Dorra Trabelsi  
- **Email:** dorra.trabelsi@itbs.tn  
- **GitHub:** [@dorratrabelsi7](https://github.com/dorratrabelsi7)  
- **GCP Project:** ecommerce-494010  

## License

MIT License — feel free to use and modify for educational and commercial purposes.

## Disclaimer

This pipeline is designed for **academic and educational purposes** with a strict $0 GCP budget constraint. Always review GCP pricing and monitor your actual usage to ensure you stay within free tier limits.

**⚠️ COST REMINDER:**  
Do NOT enable Dataflow (Compute Engine), Cloud Run, or Cloud SQL — these services incur costs and are NOT part of the free tier.
