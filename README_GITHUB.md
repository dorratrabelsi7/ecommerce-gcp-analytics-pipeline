# eCommerce Analytics Pipeline - GCP Cloud-Native

> A complete cloud-native data analytics pipeline for real-time e-commerce data processing using Google Cloud Platform (GCP) services.

## 🎯 Project Overview

This project implements a production-ready **Dataflow pipeline** for processing e-commerce data in real-time on Google Cloud Platform. It includes:

- **Real-time ingestion** via Pub/Sub
- **Data transformation** with Apache Beam on Dataflow
- **Analytics storage** in BigQuery
- **Interactive dashboards** via Looker Studio

**Architecture:**
```
Cloud Storage → Cloud Functions → Pub/Sub → Dataflow → BigQuery → Looker Studio
```

## 🚀 Quick Start

### Prerequisites
- GCP account with billing enabled
- `gcloud` CLI installed
- Python 3.8+
- Service account with appropriate permissions

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ecommerce-gcp-analytics-pipeline.git
cd ecommerce-gcp-analytics-pipeline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Deployment (15 minutes)

```bash
# 1. Authenticate with GCP
gcloud auth login
gcloud config set project ecommerce-494010

# 2. Run automated deployment
bash deploy/deploy_dataflow.sh ecommerce-494010 europe-west1

# 3. Monitor the pipeline
gcloud dataflow jobs list --region europe-west1
```

### Test the Pipeline

```bash
# Publish test data
python beam/publish_test_data.py \
    --project ecommerce-494010 \
    --input data/raw/orders.csv \
    --topic orders-realtime \
    --rate 5

# Verify data in BigQuery
bq query 'SELECT COUNT(*) FROM ecommerce-494010.ecommerce_analytics.orders_stream'
```

## 📁 Project Structure

```
ecommerce-gcp-analytics-pipeline/
├── beam/                              # Apache Beam pipelines
│   ├── dataflow_pipeline_gcp.py       # Main Dataflow pipeline
│   ├── publish_test_data.py           # Pub/Sub test publisher
│   ├── test_gcp_pipeline.py           # GCP connectivity tests
│   ├── DATAFLOW_GCP_GUIDE.md          # Deployment guide
│   └── schemas/                       # BigQuery schemas
├── deploy/                            # Deployment scripts
│   └── deploy_dataflow.sh             # Automated GCP setup
├── scripts/                           # Data generation scripts
│   ├── generate_data.py
│   ├── prepare_data.py
│   └── load_to_bq.py
├── sql/                               # BigQuery SQL queries
│   ├── 01_create_tables.sql
│   ├── 02_create_views.sql
│   └── 03_advanced_analytics.sql
├── data/                              # Sample data files
│   ├── raw/                           # Raw CSV/JSON files
│   └── clean/                         # Cleaned data
├── docs/                              # Documentation
│   └── architecture.md
├── requirements.txt                   # Python dependencies
├── START_HERE.md                      # Quick start guide
└── README.md                          # This file
```

## 🔧 Key Features

- **Real-time Processing**: Stream data via Pub/Sub to Dataflow
- **Data Validation**: Validate required fields, remove nulls and duplicates
- **Data Enrichment**: Add processing metadata and timestamps
- **Metrics Calculation**: Aggregate daily KPIs (revenue, order count, etc.)
- **Error Handling**: Separate error table for failed records
- **BigQuery Integration**: Write directly to BigQuery tables
- **Automated Deployment**: One-command deployment via shell script
- **Production-Ready**: Includes logging, monitoring, and error handling

## 📊 Data Pipeline

The pipeline processes 4 data streams:

1. **Orders** - Transaction data with amounts, status, dates
2. **Clients** - Customer demographic data
3. **Incidents** - Bug reports and support tickets
4. **Page Views** - Web analytics and user navigation

### Processing Steps
```
Raw Data
  ↓
Parse JSON/CSV
  ↓
Validate (required fields)
  ↓
Remove Nulls & Duplicates
  ↓
Enrich (add metadata)
  ↓
Aggregate (calculate metrics)
  ↓
Write to BigQuery
  ↓
Error Table (failed records)
```

## 📋 Technologies Used

- **Apache Beam** - Unified batch/streaming model
- **Google Cloud Dataflow** - Managed Apache Beam service
- **Google Cloud Pub/Sub** - Real-time messaging
- **Google BigQuery** - Data warehouse
- **Looker Studio** - Data visualization
- **Cloud Storage** - Raw data storage
- **Cloud Functions** - Serverless triggers

## 🧪 Testing

### Test GCP Connectivity
```bash
python beam/test_gcp_pipeline.py \
    --project ecommerce-494010 \
    --region europe-west1
```

### Monitor Dataflow Job
```bash
gcloud dataflow jobs list --region europe-west1
gcloud dataflow jobs describe JOB_ID --region europe-west1
gcloud dataflow jobs stream-logs JOB_ID --region europe-west1
```

### Query BigQuery
```bash
bq query --use_legacy_sql=false '
    SELECT 
        COUNT(*) as total_records,
        COUNT(DISTINCT client_id) as unique_clients,
        SUM(CAST(total_amount AS FLOAT64)) as total_revenue
    FROM `ecommerce-494010.ecommerce_analytics.orders_stream`
'
```

## 📈 Performance

- **Throughput**: ~100-1000 messages/second (depending on VM size)
- **Latency**: 1-2 minutes end-to-end
- **Cost**: ~$100-200/month with Google Cloud free credits ($300)

## 📚 Documentation

- [START_HERE.md](START_HERE.md) - Quick start commands
- [DATAFLOW_GCP_GUIDE.md](beam/DATAFLOW_GCP_GUIDE.md) - Detailed deployment guide
- [SOLUTION_FINAL.md](beam/SOLUTION_FINAL.md) - Architecture overview
- [docs/architecture.md](docs/architecture.md) - System architecture

## 🛠️ Troubleshooting

### Topic does not exist
```bash
gcloud pubsub topics create orders-realtime
gcloud pubsub topics create clients-realtime
# ... create other topics
```

### BigQuery table not found
```bash
bq mk --dataset ecommerce_analytics
bq mk --table ecommerce_analytics.orders_stream schema.json
```

### Dataflow job failed
```bash
gcloud dataflow jobs describe JOB_ID --region europe-west1
# Check logs in Cloud Logging
```

## 🚦 Deployment Stages

1. ✅ **Local Development** - Test with sample data
2. ✅ **GCP Setup** - Create cloud resources
3. ✅ **Pipeline Deployment** - Launch Dataflow job
4. ✅ **Data Publishing** - Send test messages to Pub/Sub
5. ✅ **Verification** - Check data in BigQuery
6. ✅ **Dashboard** - Create Looker Studio visualizations

## 📊 Example Queries

### Revenue by Region
```sql
SELECT 
    region,
    DATE(date_commande) as date,
    SUM(total_amount) as revenue,
    COUNT(*) as orders
FROM `ecommerce-494010.ecommerce_analytics.orders_stream`
GROUP BY region, date
ORDER BY date DESC;
```

### Inactive Clients
```sql
SELECT 
    c.client_id,
    c.email,
    MAX(o.date_commande) as last_order_date,
    CURRENT_TIMESTAMP() as checked_at
FROM `ecommerce-494010.ecommerce_analytics.clients_stream` c
LEFT JOIN `ecommerce-494010.ecommerce_analytics.orders_stream` o 
    ON c.client_id = o.client_id
GROUP BY c.client_id, c.email
HAVING last_order_date < DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY);
```

## 🔐 Security

- Use service accounts for authentication
- Enable VPC Service Controls for data protection
- Use Customer-Managed Encryption Keys (CMEK) for sensitive data
- Enable audit logging for compliance

## 📝 Costs

Estimated monthly costs:

| Service | Cost |
|---------|------|
| Dataflow | $50-100 |
| Pub/Sub | $5-10 |
| BigQuery | $10-20 |
| Cloud Storage | $2-5 |
| **Total** | **$70-150** |

*Note: Google Cloud provides $300 free credits for new accounts*

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Authors

- **Mohamed Najeh ISSAOUI** - IT Business School
- Contributors welcome!

## 📞 Support

- 📖 [Documentation](docs/)
- 🐛 [Issues](https://github.com/yourusername/ecommerce-gcp-analytics-pipeline/issues)
- 💬 [Discussions](https://github.com/yourusername/ecommerce-gcp-analytics-pipeline/discussions)

## 🔗 Related Resources

- [Apache Beam Documentation](https://beam.apache.org/)
- [Google Cloud Dataflow](https://cloud.google.com/dataflow/docs)
- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)
- [Pub/Sub Documentation](https://cloud.google.com/pubsub/docs)

---

**Last Updated:** May 1, 2026  
**Status:** ✅ Production Ready
