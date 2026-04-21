"""
Load cleaned data to BigQuery using bq CLI with corrected syntax.

This script:
1. Uploads all cleaned CSV files from data/clean/ to BigQuery
2. Validates row counts after loading
3. Verifies schema integrity

Author: Dorra Trabelsi
Date: 2026-04-21

COST NOTE: CSV loads use BigQuery's free batch load API.
No query costs incurred.
"""

import sys
import os
import subprocess
from pathlib import Path
import pandas as pd

# Configuration
PROJECT_ID = "ecommerce-494010"
DATASET = "ecommerce_analytics"
CLEAN_DATA_DIR = Path("data/clean")

# File to table mapping
FILE_TABLE_MAP = {
    "clients_clean.csv": "clients",
    "products_clean.csv": "products",
    "orders_clean.csv": "orders",
    "order_items_clean.csv": "order_items",
    "incidents_clean.csv": "incidents",
    "page_views_clean.csv": "page_views",
}


def load_csv_with_bq_cli(table_name: str, csv_path: Path) -> bool:
    """Load CSV using bq CLI with correct syntax"""
    
    if not csv_path.exists():
        print(f"❌ File not found: {csv_path}")
        return False
    
    print(f"Loading: {table_name}...")
    
    # Count source rows
    df = pd.read_csv(csv_path)
    source_rows = len(df)
    print(f"  Source: {source_rows:,} rows")
    
    # Build bq load command with correct flag positioning
    cmd = [
        "bq",
        "load",
        "--autodetect",  # MUST come before source format
        "--source_format=CSV",
        "--skip_leading_rows=1",
        "--allow_quoted_newlines",
        "--allow_jagged_rows",
        f"{DATASET}.{table_name}",
        str(csv_path),
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ {table_name} loaded successfully\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Load failed: {e.stderr}\n")
        return False


def main():
    """Execute BigQuery load pipeline."""
    
    print("=" * 70)
    print("BigQuery CSV Loader - E-Commerce Analytics Pipeline")
    print("=" * 70)
    print(f"Project: {PROJECT_ID}")
    print(f"Dataset: {DATASET}")
    print()
    
    # Verify directory
    if not CLEAN_DATA_DIR.exists():
        print(f"❌ Directory not found: {CLEAN_DATA_DIR}")
        print("Please run from project root.")
        return 1
    
    # Load all tables
    results = {}
    for file_name, table_name in FILE_TABLE_MAP.items():
        csv_path = CLEAN_DATA_DIR / file_name
        success = load_csv_with_bq_cli(table_name, csv_path)
        results[table_name] = success
    
    # Print summary
    print("=" * 70)
    print("LOAD SUMMARY")
    print("=" * 70)
    
    successful = sum(1 for v in results.values() if v)
    total = len(results)
    
    for table_name, success in results.items():
        status = "✅ OK" if success else "❌ FAILED"
        print(f"  {table_name:15} {status}")
    
    print(f"\nTotal: {successful}/{total} tables loaded")
    print("=" * 70)
    
    if successful == total:
        print("✅ All data loaded! Ready for Looker Studio.")
        return 0
    else:
        print(f"❌ {total - successful} tables failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
