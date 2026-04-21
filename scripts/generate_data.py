"""
Synthetic data generation for e-commerce analytics pipeline.

This module generates fully synthetic and internally consistent data using
Faker, Pandas, and NumPy. All data is generated locally with no external
services required.

Author: Dorra Trabelsi
Date: 2026-04-21
Cost: $0 (local generation only)

Volume targets:
- NB_CLIENTS = 2,000
- NB_PRODUCTS = 50
- NB_ORDERS = 15,000
- NB_INCIDENTS = 3,000
- NB_SESSIONS = 50,000
- DATE_RANGE = 2022-01-01 to 2024-06-01
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

# Configuration
NB_CLIENTS = 2_000
NB_PRODUCTS = 50
NB_ORDERS = 15_000
NB_INCIDENTS = 3_000
NB_SESSIONS = 50_000
DATE_START = datetime(2022, 1, 1)
DATE_END = datetime(2024, 6, 1)

# Output directory
DATA_DIR = Path("data/raw")
DOCS_DIR = Path("docs")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Faker
fake = Faker("fr_FR")
np.random.seed(42)


# ============================================================================
# Dataset 1: CLIENTS
# ============================================================================

def generate_clients():
    """Generate client master data with realistic demographics."""
    logger.info(f"Generating {NB_CLIENTS} clients...")
    
    # Country-to-cities mapping
    cities_by_country = {
        "France": ["Paris", "Lyon", "Marseille", "Toulouse", "Nice", "Nantes", "Bordeaux", "Lille"],
        "Belgium": ["Brussels", "Antwerp", "Ghent", "Charleroi", "Liège"],
        "Switzerland": ["Zurich", "Geneva", "Basel", "Bern", "Lucerne"],
        "Canada": ["Toronto", "Montreal", "Vancouver", "Calgary", "Ottawa"],
        "Morocco": ["Casablanca", "Rabat", "Marrakesh", "Fez", "Tangier"],
        "Tunisia": ["Tunis", "Sfax", "Sousse", "Kairouan", "Gafsa"],
        "Senegal": ["Dakar", "Kaolack", "Saint-Louis", "Thiès", "Tambacounda"],
    }
    
    # Country distribution (weighted)
    countries = np.random.choice(
        list(cities_by_country.keys()),
        size=NB_CLIENTS,
        p=[0.55, 0.15, 0.10, 0.08, 0.05, 0.04, 0.03]
    )
    
    clients = []
    for i in range(NB_CLIENTS):
        client_id = f"C{i+1:04d}"
        country = countries[i]
        city = np.random.choice(cities_by_country[country])
        gender = np.random.choice(["M", "F", "Non-binary"], p=[0.48, 0.48, 0.04])
        registration_date = fake.date_between_dates(date_start=DATE_START, date_end=DATE_END)
        
        # Determine segment based on registration date (last 6 months = "new")
        six_months_before_end = DATE_END - timedelta(days=180)
        segment = "new" if pd.to_datetime(registration_date) >= six_months_before_end else "regular"
        
        clients.append({
            "client_id": client_id,
            "last_name": fake.last_name(),
            "first_name": fake.first_name(),
            "email": fake.email(),
            "age": np.random.randint(18, 75),
            "gender": gender,
            "country": country,
            "city": city,
            "phone": fake.phone_number(),
            "registration_date": registration_date,
            "segment": segment,
        })
    
    df = pd.DataFrame(clients)
    df.to_csv(DATA_DIR / "clients.csv", index=False)
    logger.info(f"✓ Generated {len(df)} clients -> data/raw/clients.csv")
    return df


# ============================================================================
# Dataset 2: PRODUCTS
# ============================================================================

def generate_products():
    """Generate product catalog with categories and pricing."""
    logger.info(f"Generating {NB_PRODUCTS} products...")
    
    categories = ["Electronics", "Audio", "Office Furniture", "Accessories", "Storage"]
    
    # Price ranges by category
    price_ranges = {
        "Electronics": (99.99, 499.99),
        "Audio": (29.99, 299.99),
        "Office Furniture": (49.99, 399.99),
        "Accessories": (9.99, 49.99),
        "Storage": (19.99, 149.99),
    }
    
    products = []
    for i in range(NB_PRODUCTS):
        product_id = f"P{i+1:03d}"
        category = np.random.choice(categories)
        min_price, max_price = price_ranges[category]
        
        products.append({
            "product_id": product_id,
            "product_name": fake.word().title() + " " + np.random.choice(["Pro", "Ultra", "Deluxe", "Basic"]),
            "category": category,
            "unit_price": round(np.random.uniform(min_price, max_price), 2),
            "stock": np.random.randint(0, 500),
        })
    
    df = pd.DataFrame(products)
    df.to_csv(DATA_DIR / "products.csv", index=False)
    logger.info(f"✓ Generated {len(df)} products -> data/raw/products.csv")
    return df


# ============================================================================
# Dataset 3: ORDERS and ORDER_ITEMS
# ============================================================================

def generate_orders_and_items(clients_df, products_df):
    """Generate orders with items and maintain FK relationships."""
    logger.info(f"Generating {NB_ORDERS} orders with items...")
    
    orders = []
    order_items = []
    
    countries_to_regions = {
        "France": "EU-FR",
        "Belgium": "EU-BE",
        "Switzerland": "EU-CH",
        "Canada": "NA-CA",
        "Morocco": "AF-MA",
        "Tunisia": "AF-TN",
        "Senegal": "AF-SN",
    }
    
    statuses = ["Delivered", "Pending", "Cancelled", "Refunded"]
    status_weights = [0.65, 0.20, 0.10, 0.05]
    payment_methods = ["Credit card", "PayPal", "Bank transfer", "Cheque"]
    payment_weights = [0.60, 0.25, 0.10, 0.05]
    
    item_id_counter = 1
    
    for i in range(NB_ORDERS):
        order_id = f"ORD{i+1:05d}"
        
        # Select random client
        client = clients_df.sample(1).iloc[0]
        client_id = client["client_id"]
        
        # Ensure order_date is after registration
        reg_date = pd.to_datetime(client["registration_date"])
        order_date = fake.date_between_dates(
            date_start=reg_date,
            date_end=DATE_END
        )
        
        status = np.random.choice(statuses, p=status_weights)
        payment_method = np.random.choice(payment_methods, p=payment_weights)
        region = countries_to_regions[client["country"]]
        
        # Generate order items (1-4 items with Poisson distribution)
        num_items = min(4, max(1, np.random.poisson(1.5)))
        total_amount = 0
        
        for _ in range(num_items):
            product = products_df.sample(1).iloc[0]
            product_id = product["product_id"]
            quantity = np.random.randint(1, 5)
            # Apply up to 5% discount
            discount_factor = np.random.uniform(0.95, 1.0)
            unit_price = round(product["unit_price"] * discount_factor, 2)
            item_total = round(quantity * unit_price, 2)
            total_amount += item_total
            
            order_items.append({
                "item_id": item_id_counter,
                "order_id": order_id,
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": unit_price,
            })
            item_id_counter += 1
        
        orders.append({
            "order_id": order_id,
            "client_id": client_id,
            "order_date": order_date,
            "status": status,
            "payment_method": payment_method,
            "region": region,
            "total_amount": round(total_amount, 2),
        })
    
    orders_df = pd.DataFrame(orders)
    items_df = pd.DataFrame(order_items)
    
    orders_df.to_csv(DATA_DIR / "orders.csv", index=False)
    items_df.to_csv(DATA_DIR / "order_items.csv", index=False)
    
    logger.info(f"✓ Generated {len(orders_df)} orders -> data/raw/orders.csv")
    logger.info(f"✓ Generated {len(items_df)} items -> data/raw/order_items.csv")
    
    return orders_df, items_df


# ============================================================================
# Dataset 4: INCIDENTS
# ============================================================================

def generate_incidents(clients_df, orders_df):
    """Generate support incidents with relationships."""
    logger.info(f"Generating {NB_INCIDENTS} incidents...")
    
    categories = ["Payment", "Delivery", "Defective product", "Login", "Customer service"]
    category_weights = [0.25, 0.35, 0.20, 0.10, 0.10]
    statuses = ["Resolved", "In progress", "Escalated", "Closed"]
    status_weights = [0.60, 0.25, 0.10, 0.05]
    priorities = ["Low", "Medium", "High", "Critical"]
    priority_weights = [0.30, 0.40, 0.20, 0.10]
    
    incidents = []
    
    for i in range(NB_INCIDENTS):
        incident_id = f"INC{i+1:04d}"
        
        # Select random client
        client = clients_df.sample(1).iloc[0]
        client_id = client["client_id"]
        reg_date = pd.to_datetime(client["registration_date"])
        
        # Report date must be after registration
        report_date = fake.date_between_dates(date_start=reg_date, date_end=DATE_END)
        
        category = np.random.choice(categories, p=category_weights)
        status = np.random.choice(statuses, p=status_weights)
        priority = np.random.choice(priorities, p=priority_weights)
        
        # Link to order 70% of the time
        order_id = None
        if np.random.random() < 0.70:
            client_orders = orders_df[orders_df["client_id"] == client_id]
            if len(client_orders) > 0:
                order_id = client_orders.sample(1).iloc[0]["order_id"]
        
        # Resolution time
        resolution_time_h = None
        if status != "In progress":
            if priority == "Critical":
                resolution_time_h = np.random.randint(1, 24)  # Under 24h
            else:
                resolution_time_h = np.random.randint(1, 168)  # 1-7 days
        
        incidents.append({
            "incident_id": incident_id,
            "client_id": client_id,
            "report_date": report_date,
            "category": category,
            "order_id": order_id,
            "status": status,
            "priority": priority,
            "resolution_time_h": resolution_time_h,
        })
    
    df = pd.DataFrame(incidents)
    df.to_csv(DATA_DIR / "incidents.csv", index=False)
    logger.info(f"✓ Generated {len(df)} incidents -> data/raw/incidents.csv")
    return df


# ============================================================================
# Dataset 5: PAGE_VIEWS / SESSIONS
# ============================================================================

def generate_page_views(clients_df):
    """Generate session and page view data."""
    logger.info(f"Generating {NB_SESSIONS} sessions with page views...")
    
    pages = [
        "/home", "/products", "/cart", "/checkout", "/profile", 
        "/support", "/deals", "/category/electronics", "/category/audio"
    ]
    page_weights = [0.20, 0.25, 0.10, 0.08, 0.07, 0.05, 0.05, 0.12, 0.08]
    
    # Duration by page (seconds)
    duration_by_page = {
        "/home": (10, 60),
        "/products": (30, 300),
        "/cart": (20, 120),
        "/checkout": (60, 600),
        "/profile": (15, 90),
        "/support": (30, 180),
        "/deals": (20, 150),
        "/category/electronics": (40, 250),
        "/category/audio": (40, 250),
    }
    
    devices = ["Mobile", "Desktop", "Tablet"]
    device_weights = [0.55, 0.40, 0.05]
    
    browsers = ["Chrome", "Safari", "Firefox", "Edge"]
    browser_weights = [0.60, 0.20, 0.12, 0.08]
    
    traffic_sources = ["Direct", "Google", "Instagram", "Email", "Referral"]
    traffic_weights = [0.30, 0.35, 0.15, 0.12, 0.08]
    
    sessions = []
    
    for i in range(NB_SESSIONS):
        session_id = f"S{i+1:06d}"
        
        # Client exists in 80% of cases
        if np.random.random() < 0.80:
            client_id = clients_df.sample(1).iloc[0]["client_id"]
        else:
            client_id = None  # Anonymous visitor
        
        page = np.random.choice(pages, p=page_weights)
        min_dur, max_dur = duration_by_page[page]
        duration_seconds = np.random.randint(min_dur, max_dur)
        
        # Bimodal distribution: peaks at 12-14:00 and 19-22:00
        hour = np.random.choice([13, 20], p=[0.5, 0.5])
        hour += np.random.randint(-2, 3)  # Add variance
        hour = max(0, min(23, hour))
        
        event_datetime = fake.date_between_dates(
            date_start=DATE_START,
            date_end=DATE_END
        ).replace(hour=hour, minute=np.random.randint(0, 60))
        
        device = np.random.choice(devices, p=device_weights)
        browser = np.random.choice(browsers, p=browser_weights)
        traffic_source = np.random.choice(traffic_sources, p=traffic_weights)
        
        sessions.append({
            "session_id": session_id,
            "client_id": client_id,
            "page": page,
            "event_datetime": event_datetime,
            "duration_seconds": duration_seconds,
            "device": device,
            "browser": browser,
            "traffic_source": traffic_source,
        })
    
    df = pd.DataFrame(sessions)
    df.to_csv(DATA_DIR / "page_views.csv", index=False)
    logger.info(f"✓ Generated {len(df)} sessions -> data/raw/page_views.csv")
    return df


# ============================================================================
# INJECT DATA QUALITY ISSUES (to be cleaned in STEP 2)
# ============================================================================

def inject_data_quality_issues():
    """Inject intentional data quality issues."""
    logger.info("Injecting intentional data quality issues...")
    
    # Load all datasets
    clients_df = pd.read_csv(DATA_DIR / "clients.csv")
    products_df = pd.read_csv(DATA_DIR / "products.csv")
    orders_df = pd.read_csv(DATA_DIR / "orders.csv")
    page_views_df = pd.read_csv(DATA_DIR / "page_views.csv")
    
    # 1. Inject 2% random NULLs on non-key columns
    for df_name, df in [("clients", clients_df), ("products", products_df)]:
        for col in df.columns[1:]:  # Skip ID columns
            null_indices = np.random.choice(df.index, size=int(0.02 * len(df)), replace=False)
            df.loc[null_indices, col] = None
    
    # 2. Inject 1% duplicate rows
    for df in [clients_df, products_df]:
        dup_count = int(0.01 * len(df))
        dup_rows = df.sample(dup_count)
        df = pd.concat([df, dup_rows], ignore_index=True)
    
    # 3. Replace "@" with "at" in 0.5% of emails
    email_indices = np.random.choice(
        clients_df.index, 
        size=int(0.005 * len(clients_df)), 
        replace=False
    )
    clients_df.loc[email_indices, "email"] = \
        clients_df.loc[email_indices, "email"].str.replace("@", "at", n=1)
    
    # 4. Set age < 10 or > 100 in 0.3% of client rows
    age_indices = np.random.choice(
        clients_df.index, 
        size=int(0.003 * len(clients_df)), 
        replace=False
    )
    for idx in age_indices:
        clients_df.loc[idx, "age"] = np.random.choice([5, 150])
    
    # Save modified datasets
    clients_df.to_csv(DATA_DIR / "clients.csv", index=False)
    products_df.to_csv(DATA_DIR / "products.csv", index=False)
    
    logger.info("✓ Data quality issues injected")


# ============================================================================
# GENERATION REPORT
# ============================================================================

def generate_report(clients_df, products_df, orders_df, items_df, incidents_df, page_views_df):
    """Generate a comprehensive data generation report."""
    logger.info("Generating data generation report...")
    
    # Calculate statistics
    total_revenue = orders_df["total_amount"].sum()
    delivered_count = (orders_df["status"] == "Delivered").sum()
    delivery_rate = (delivered_count / len(orders_df)) * 100
    
    # Top 5 products by revenue
    product_revenue = items_df.groupby("product_id").apply(
        lambda x: (x["quantity"] * x["unit_price"]).sum()
    ).sort_values(ascending=False).head(5)
    
    # Country distribution
    country_dist = clients_df["country"].value_counts()
    
    report = f"""
================================================================================
E-COMMERCE ANALYTICS PIPELINE - DATA GENERATION REPORT
Generated: {datetime.now().isoformat()}
================================================================================

DATASET VOLUMES
================================================================================
Clients:           {len(clients_df):,} rows
Products:          {len(products_df):,} rows
Orders:            {len(orders_df):,} rows
Order Items:       {len(items_df):,} rows
Incidents:         {len(incidents_df):,} rows
Page Views:        {len(page_views_df):,} rows
TOTAL:             {len(clients_df) + len(products_df) + len(orders_df) + len(items_df) + len(incidents_df) + len(page_views_df):,} rows

KEY METRICS
================================================================================
Total Simulated Revenue:     €{total_revenue:,.2f}
Orders Delivered:            {delivered_count:,} ({delivery_rate:.1f}%)
Average Basket Size:         €{orders_df["total_amount"].mean():.2f}
Orders per Client:           {len(orders_df) / len(clients_df):.2f}

GEOGRAPHIC DISTRIBUTION (CLIENTS)
================================================================================
{country_dist.to_string()}

TOP 5 PRODUCTS BY REVENUE
================================================================================
{product_revenue.to_string()}

DATA QUALITY ISSUES INJECTED
================================================================================
- 2% random NULL values on non-key columns
- 1% full duplicate rows
- 0.5% malformed emails (@ replaced with "at")
- 0.3% invalid ages (< 10 or > 100)

DATE RANGE
================================================================================
Start Date: {DATE_START.date()}
End Date:   {DATE_END.date()}
Duration:   {(DATE_END - DATE_START).days} days

COST NOTE
================================================================================
Data generation runs entirely on your local machine using Faker, Pandas, and
NumPy. No GCP resources are consumed. This is 100% free ($0 cost).

================================================================================
"""
    
    # Save report
    report_file = DOCS_DIR / "data_generation_report.txt"
    with open(report_file, "w") as f:
        f.write(report)
    
    logger.info(f"✓ Report saved -> docs/data_generation_report.txt")
    print(report)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Execute data generation pipeline."""
    try:
        logger.info("=" * 80)
        logger.info("E-COMMERCE ANALYTICS PIPELINE - DATA GENERATION")
        logger.info(f"Target Volume: {NB_CLIENTS} clients, {NB_ORDERS} orders, {NB_SESSIONS} sessions")
        logger.info("=" * 80)
        
        # Generate datasets
        clients_df = generate_clients()
        products_df = generate_products()
        orders_df, items_df = generate_orders_and_items(clients_df, products_df)
        incidents_df = generate_incidents(clients_df, orders_df)
        page_views_df = generate_page_views(clients_df)
        
        # Inject quality issues
        inject_data_quality_issues()
        
        # Generate report
        generate_report(clients_df, products_df, orders_df, items_df, incidents_df, page_views_df)
        
        logger.info("=" * 80)
        logger.info("✓ Data generation complete!")
        logger.info(f"  Output directory: {DATA_DIR.absolute()}")
        logger.info("=" * 80)
        
        return 0
    
    except Exception as e:
        logger.error(f"✗ Data generation failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
