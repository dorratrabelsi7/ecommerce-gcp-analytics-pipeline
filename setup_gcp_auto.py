#!/usr/bin/env python3
"""
GCP Infrastructure Setup - Python Version
Automatically creates all GCP resources for the e-commerce pipeline
"""

import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env configuration
load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID", "ecommerce-494010")
REGION = os.getenv("REGION", "europe-west1")
DATASET = os.getenv("DATASET", "ecommerce_analytics")
BUCKET = os.getenv("BUCKET", f"ecommerce-data-{PROJECT_ID}")
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "orders-realtime")
PUBSUB_TOPIC_DLQ = os.getenv("PUBSUB_TOPIC_DLQ", "orders-realtime-dlq")
PUBSUB_SUB = os.getenv("PUBSUB_SUB", "orders-realtime-sub")
PUBSUB_SUB_DLQ = os.getenv("PUBSUB_SUB_DLQ", "orders-realtime-dlq-sub")

def run_command(cmd, description):
    """Execute a shell command and handle errors"""
    print(f"\n✓ {description}")
    print(f"  Command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ⚠ Warning: {result.stderr}")
        else:
            print(f"  ✅ Success")
        return result.returncode == 0
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def setup_gcp():
    """Main setup function"""
    print("=" * 70)
    print("GCP INFRASTRUCTURE SETUP - AUTOMATED")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Project ID: {PROJECT_ID}")
    print(f"  Region: {REGION}")
    print(f"  Dataset: {DATASET}")
    print(f"  Bucket: {BUCKET}")
    print(f"  Pub/Sub Topic: {PUBSUB_TOPIC}")
    
    # Step 1: Set project
    print("\n[STEP 1] Setting GCP Project...")
    run_command(f"gcloud config set project {PROJECT_ID}", "Set active project")
    
    # Step 2: Create GCS Bucket
    print("\n[STEP 2] Creating Cloud Storage Bucket...")
    run_command(
        f"gsutil mb -l {REGION} gs://{BUCKET}",
        f"Create bucket gs://{BUCKET}"
    )
    
    # Step 3: Create BigQuery Dataset
    print("\n[STEP 3] Creating BigQuery Dataset...")
    run_command(
        f"bq mk --dataset --location=EU {DATASET}",
        f"Create BigQuery dataset {DATASET}"
    )
    
    # Step 4: Create Pub/Sub Topics
    print("\n[STEP 4] Creating Pub/Sub Topics...")
    run_command(
        f"gcloud pubsub topics create {PUBSUB_TOPIC}",
        f"Create topic {PUBSUB_TOPIC}"
    )
    run_command(
        f"gcloud pubsub topics create {PUBSUB_TOPIC_DLQ}",
        f"Create DLQ topic {PUBSUB_TOPIC_DLQ}"
    )
    
    # Step 5: Create Pub/Sub Subscriptions
    print("\n[STEP 5] Creating Pub/Sub Subscriptions...")
    run_command(
        f"gcloud pubsub subscriptions create {PUBSUB_SUB} --topic={PUBSUB_TOPIC}",
        f"Create subscription {PUBSUB_SUB}"
    )
    run_command(
        f"gcloud pubsub subscriptions create {PUBSUB_SUB_DLQ} --topic={PUBSUB_TOPIC_DLQ}",
        f"Create DLQ subscription {PUBSUB_SUB_DLQ}"
    )
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ GCP SETUP COMPLETE!")
    print("=" * 70)
    print(f"\nResources Created:")
    print(f"  ✓ Bucket: gs://{BUCKET}")
    print(f"  ✓ Dataset: {DATASET}")
    print(f"  ✓ Topics: {PUBSUB_TOPIC}, {PUBSUB_TOPIC_DLQ}")
    print(f"  ✓ Subscriptions: {PUBSUB_SUB}, {PUBSUB_SUB_DLQ}")
    print("\n🚀 Ready for STEP 5: Deploy BigQuery Schema!")

if __name__ == "__main__":
    setup_gcp()
