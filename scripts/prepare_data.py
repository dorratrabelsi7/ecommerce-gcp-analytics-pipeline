"""
Data cleaning and validation for e-commerce analytics pipeline.

This module loads raw synthetic data and performs comprehensive cleaning:
- Drop duplicates and rows with NULL keys
- Fix malformed emails
- Remove invalid ages
- Parse dates
- Round monetary values
- Recompute derived fields

Author: Dorra Trabelsi
Date: 2026-04-21
Cost: $0 (local processing only)
"""

import os
import sys
import json
import re
import logging
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

# Configuration
RAW_DATA_DIR = Path("data/raw")
CLEAN_DATA_DIR = Path("data/clean")
DOCS_DIR = Path("docs")

CLEAN_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging - structured JSON format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# CLEANING OPERATIONS
# ============================================================================

class DataCleaner:
    """Handles data cleaning for all datasets."""
    
    def __init__(self):
        self.cleaning_report = {}
    
    def clean_clients(self, df):
        """Clean clients dataset."""
        logger.info(f"Cleaning clients: starting with {len(df)} rows")
        initial_count = len(df)
        
        # 1. Remove duplicates
        before_dup = len(df)
        df = df.drop_duplicates()
        dup_removed = before_dup - len(df)
        logger.info(f"  - Removed {dup_removed} duplicate rows")
        
        # 2. Drop rows with NULL in key columns
        before_null = len(df)
        df = df.dropna(subset=["client_id", "email"])
        null_removed = before_null - len(df)
        logger.info(f"  - Removed {null_removed} rows with NULL keys")
        
        # 3. Fix malformed emails (at → @)
        df["email"] = df["email"].str.replace("at@", "@", regex=False)
        df["email"] = df["email"].str.replace("at", "@", regex=False)
        malformed = (df["email"].str.count("at") > 0).sum()
        logger.info(f"  - Fixed email format")
        
        # 4. Remove invalid ages
        before_age = len(df)
        df = df[(df["age"] >= 14) & (df["age"] <= 100)]
        age_removed = before_age - len(df)
        logger.info(f"  - Removed {age_removed} rows with invalid ages")
        
        # 5. Parse registration_date to datetime
        df["registration_date"] = pd.to_datetime(df["registration_date"], errors="coerce")
        
        final_count = len(df)
        self.cleaning_report["clients"] = {
            "initial": initial_count,
            "final": final_count,
            "removed": initial_count - final_count,
            "duplicates_removed": dup_removed,
            "null_keys_removed": null_removed,
            "invalid_ages_removed": age_removed,
        }
        
        logger.info(f"✓ Clients cleaned: {final_count} rows retained ({100*final_count/initial_count:.1f}%)")
        return df
    
    def clean_products(self, df):
        """Clean products dataset."""
        logger.info(f"Cleaning products: starting with {len(df)} rows")
        initial_count = len(df)
        
        # 1. Remove duplicates
        before_dup = len(df)
        df = df.drop_duplicates()
        dup_removed = before_dup - len(df)
        logger.info(f"  - Removed {dup_removed} duplicate rows")
        
        # 2. Drop rows with NULL in key columns
        before_null = len(df)
        df = df.dropna(subset=["product_id", "category"])
        null_removed = before_null - len(df)
        logger.info(f"  - Removed {null_removed} rows with NULL keys")
        
        # 3. Round monetary values
        df["unit_price"] = df["unit_price"].round(2)
        logger.info(f"  - Rounded prices to 2 decimals")
        
        final_count = len(df)
        self.cleaning_report["products"] = {
            "initial": initial_count,
            "final": final_count,
            "removed": initial_count - final_count,
            "duplicates_removed": dup_removed,
            "null_keys_removed": null_removed,
        }
        
        logger.info(f"✓ Products cleaned: {final_count} rows retained")
        return df
    
    def clean_orders(self, df):
        """Clean orders dataset."""
        logger.info(f"Cleaning orders: starting with {len(df)} rows")
        initial_count = len(df)
        
        # 1. Remove duplicates
        df = df.drop_duplicates()
        
        # 2. Drop rows with NULL in key columns
        before_null = len(df)
        df = df.dropna(subset=["order_id", "client_id"])
        null_removed = before_null - len(df)
        
        # 3. Parse order_date
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
        
        # 4. Round total_amount
        df["total_amount"] = df["total_amount"].round(2)
        
        final_count = len(df)
        self.cleaning_report["orders"] = {
            "initial": initial_count,
            "final": final_count,
            "removed": initial_count - final_count,
            "null_keys_removed": null_removed,
        }
        
        logger.info(f"✓ Orders cleaned: {final_count} rows retained")
        return df
    
    def clean_order_items(self, df):
        """Clean order items dataset."""
        logger.info(f"Cleaning order_items: starting with {len(df)} rows")
        initial_count = len(df)
        
        # 1. Remove duplicates
        df = df.drop_duplicates()
        
        # 2. Drop rows with NULL in key columns
        before_null = len(df)
        df = df.dropna(subset=["item_id", "order_id", "product_id"])
        null_removed = before_null - len(df)
        
        # 3. Round prices
        df["unit_price"] = df["unit_price"].round(2)
        
        final_count = len(df)
        self.cleaning_report["order_items"] = {
            "initial": initial_count,
            "final": final_count,
            "removed": initial_count - final_count,
            "null_keys_removed": null_removed,
        }
        
        logger.info(f"✓ Order items cleaned: {final_count} rows retained")
        return df
    
    def clean_incidents(self, df):
        """Clean incidents dataset."""
        logger.info(f"Cleaning incidents: starting with {len(df)} rows")
        initial_count = len(df)
        
        # 1. Remove duplicates
        df = df.drop_duplicates()
        
        # 2. Drop rows with NULL in key columns
        before_null = len(df)
        df = df.dropna(subset=["incident_id", "client_id"])
        null_removed = before_null - len(df)
        
        # 3. Parse report_date
        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
        
        final_count = len(df)
        self.cleaning_report["incidents"] = {
            "initial": initial_count,
            "final": final_count,
            "removed": initial_count - final_count,
            "null_keys_removed": null_removed,
        }
        
        logger.info(f"✓ Incidents cleaned: {final_count} rows retained")
        return df
    
    def clean_page_views(self, df):
        """Clean page views / sessions dataset."""
        logger.info(f"Cleaning page_views: starting with {len(df)} rows")
        initial_count = len(df)
        
        # 1. Remove duplicates
        df = df.drop_duplicates()
        
        # 2. Drop rows with NULL in key columns
        before_null = len(df)
        df = df.dropna(subset=["session_id"])
        null_removed = before_null - len(df)
        
        # 3. Parse event_datetime
        df["event_datetime"] = pd.to_datetime(df["event_datetime"], errors="coerce")
        
        final_count = len(df)
        self.cleaning_report["page_views"] = {
            "initial": initial_count,
            "final": final_count,
            "removed": initial_count - final_count,
            "null_keys_removed": null_removed,
        }
        
        logger.info(f"✓ Page views cleaned: {final_count} rows retained")
        return df
    
    def recompute_order_totals(self, orders_df, items_df):
        """Recompute order totals from order items (source of truth)."""
        logger.info("Recomputing order total amounts from items...")
        
        # Calculate totals from items
        item_totals = items_df.groupby("order_id").apply(
            lambda x: (x["quantity"] * x["unit_price"]).sum()
        ).round(2)
        
        # Update orders
        for order_id, total in item_totals.items():
            orders_df.loc[orders_df["order_id"] == order_id, "total_amount"] = total
        
        logger.info("✓ Order totals recomputed")
        return orders_df
    
    def generate_report(self):
        """Generate cleaning report."""
        total_initial = sum(r.get("initial", 0) for r in self.cleaning_report.values())
        total_final = sum(r.get("final", 0) for r in self.cleaning_report.values())
        total_removed = total_initial - total_final
        
        report = f"""
================================================================================
E-COMMERCE ANALYTICS PIPELINE - DATA CLEANING REPORT
Generated: {datetime.now().isoformat()}
================================================================================

DATASET CLEANING SUMMARY
================================================================================

"""
        
        for dataset, metrics in self.cleaning_report.items():
            initial = metrics.get("initial", 0)
            final = metrics.get("final", 0)
            removed = metrics.get("removed", 0)
            retention = (final / initial * 100) if initial > 0 else 0
            
            report += f"\n{dataset.upper()}\n"
            report += f"  Initial rows:     {initial:,}\n"
            report += f"  Removed:          {removed:,}\n"
            report += f"  Final rows:       {final:,}\n"
            report += f"  Retention rate:   {retention:.2f}%\n"
            
            for key, val in metrics.items():
                if key not in ["initial", "final", "removed"]:
                    report += f"  - {key.replace('_', ' ').title()}: {val}\n"
        
        report += f"""
OVERALL STATISTICS
================================================================================
Total Initial Rows:     {total_initial:,}
Total Removed:          {total_removed:,}
Total Final Rows:       {total_final:,}
Overall Retention:      {(total_final/total_initial*100):.2f}%

DATA QUALITY IMPROVEMENTS
================================================================================
✓ Duplicates removed
✓ NULL keys removed
✓ Emails fixed (at → @)
✓ Invalid ages removed
✓ Dates parsed to datetime
✓ Monetary values rounded to 2 decimals
✓ Order totals recomputed from items (source of truth)

================================================================================
"""
        
        # Save report
        report_file = DOCS_DIR / "cleaning_report.txt"
        with open(report_file, "w") as f:
            f.write(report)
        
        logger.info(f"✓ Cleaning report saved -> docs/cleaning_report.txt")
        print(report)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Execute data cleaning pipeline."""
    try:
        logger.info("=" * 80)
        logger.info("E-COMMERCE ANALYTICS PIPELINE - DATA CLEANING")
        logger.info("=" * 80)
        
        # Initialize cleaner
        cleaner = DataCleaner()
        
        # Load raw datasets
        logger.info("Loading raw datasets...")
        clients_df = pd.read_csv(RAW_DATA_DIR / "clients.csv")
        products_df = pd.read_csv(RAW_DATA_DIR / "products.csv")
        orders_df = pd.read_csv(RAW_DATA_DIR / "orders.csv")
        items_df = pd.read_csv(RAW_DATA_DIR / "order_items.csv")
        incidents_df = pd.read_csv(RAW_DATA_DIR / "incidents.csv")
        page_views_df = pd.read_csv(RAW_DATA_DIR / "page_views.csv")
        
        # Clean each dataset
        logger.info("=" * 80)
        logger.info("CLEANING DATASETS")
        logger.info("=" * 80)
        
        clients_df = cleaner.clean_clients(clients_df)
        products_df = cleaner.clean_products(products_df)
        orders_df = cleaner.clean_orders(orders_df)
        items_df = cleaner.clean_order_items(items_df)
        incidents_df = cleaner.clean_incidents(incidents_df)
        page_views_df = cleaner.clean_page_views(page_views_df)
        
        # Recompute derived fields
        logger.info("=" * 80)
        logger.info("RECOMPUTING DERIVED FIELDS")
        logger.info("=" * 80)
        
        orders_df = cleaner.recompute_order_totals(orders_df, items_df)
        
        # Save cleaned datasets
        logger.info("=" * 80)
        logger.info("SAVING CLEANED DATASETS")
        logger.info("=" * 80)
        
        clients_df.to_csv(CLEAN_DATA_DIR / "clients_clean.csv", index=False)
        logger.info("✓ clients_clean.csv saved")
        
        products_df.to_csv(CLEAN_DATA_DIR / "products_clean.csv", index=False)
        logger.info("✓ products_clean.csv saved")
        
        orders_df.to_csv(CLEAN_DATA_DIR / "orders_clean.csv", index=False)
        logger.info("✓ orders_clean.csv saved")
        
        items_df.to_csv(CLEAN_DATA_DIR / "order_items_clean.csv", index=False)
        logger.info("✓ order_items_clean.csv saved")
        
        incidents_df.to_csv(CLEAN_DATA_DIR / "incidents_clean.csv", index=False)
        logger.info("✓ incidents_clean.csv saved")
        
        page_views_df.to_csv(CLEAN_DATA_DIR / "page_views_clean.csv", index=False)
        logger.info("✓ page_views_clean.csv saved")
        
        # Generate report
        logger.info("=" * 80)
        logger.info("GENERATING REPORT")
        logger.info("=" * 80)
        
        cleaner.generate_report()
        
        logger.info("=" * 80)
        logger.info("✓ Data cleaning complete!")
        logger.info(f"  Output directory: {CLEAN_DATA_DIR.absolute()}")
        logger.info("=" * 80)
        
        return 0
    
    except Exception as e:
        logger.error(f"✗ Data cleaning failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
