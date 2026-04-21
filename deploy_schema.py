#!/usr/bin/env python3
"""
BigQuery Schema Deployment Script
Replaces placeholders in SQL files and deploys to BigQuery
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load configuration
load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID", "ecommerce-494010")
DATASET = os.getenv("DATASET", "ecommerce_analytics")

def replace_placeholders(sql_content):
    """Replace {project_id} and {dataset} placeholders"""
    return sql_content.replace("{project_id}", PROJECT_ID).replace("{dataset}", DATASET)

def deploy_bigquery_schema():
    """Deploy BigQuery schema"""
    
    print("=" * 70)
    print("BIGQUERY SCHEMA DEPLOYMENT")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Project ID: {PROJECT_ID}")
    print(f"  Dataset: {DATASET}")
    
    # Step 1: Create tables
    print("\n[STEP 1] Creating BigQuery Tables...")
    sql_file = Path("sql/01_create_tables.sql")
    if sql_file.exists():
        with open(sql_file, "r") as f:
            sql_content = f.read()
        
        sql_content = replace_placeholders(sql_content)
        
        # Execute
        cmd = f"bq query --use_legacy_sql=false --project_id={PROJECT_ID}"
        proc = subprocess.Popen(cmd.split(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(input=sql_content.encode())
        
        if proc.returncode == 0:
            print("  ✅ Tables created successfully")
        else:
            print(f"  ⚠ Tables creation output:\n{stdout.decode()}")
    else:
        print(f"  ❌ File not found: {sql_file}")
    
    # Step 2: Create views
    print("\n[STEP 2] Creating BigQuery Views...")
    sql_file = Path("sql/02_create_views.sql")
    if sql_file.exists():
        with open(sql_file, "r") as f:
            sql_content = f.read()
        
        sql_content = replace_placeholders(sql_content)
        
        cmd = f"bq query --use_legacy_sql=false --project_id={PROJECT_ID}"
        proc = subprocess.Popen(cmd.split(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(input=sql_content.encode())
        
        if proc.returncode == 0:
            print("  ✅ Views created successfully")
        else:
            print(f"  ⚠ Views creation output:\n{stdout.decode()}")
    else:
        print(f"  ❌ File not found: {sql_file}")
    
    # Step 3: Verify
    print("\n[STEP 3] Verifying Schema...")
    cmd = f"bq ls --project_id={PROJECT_ID} {DATASET}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"  ✅ Dataset contents:\n{result.stdout}")
    else:
        print(f"  ❌ Error: {result.stderr}")
    
    print("\n" + "=" * 70)
    print("✅ BIGQUERY SCHEMA DEPLOYMENT COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    deploy_bigquery_schema()
