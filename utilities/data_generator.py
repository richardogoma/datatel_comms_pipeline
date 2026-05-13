import argparse
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import numpy as np
import pandas as pd
from faker import Faker
from google.cloud import storage
from tqdm import tqdm

fake = Faker()
np.random.seed(42)
random.seed(42)

# =========================
# SCALE CONFIG
# =========================
NUM_CUSTOMERS = 100_000
NUM_TRANSACTIONS = 1_500_000
NUM_SESSIONS = 3_000_000

# =========================
# HELPERS
# =========================
def generate_skewed_ids(n_ids, size):
    weights = np.random.zipf(2, n_ids)
    weights = weights / weights.sum()
    return np.random.choice(np.arange(1, n_ids + 1), size=size, p=weights)


def get_table_name(filename):
    return filename.replace("src_", "").replace(".csv", "")


def upload_file_to_gcs(client, bucket_name, local_file_path, gcs_path):
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(local_file_path)
    return f"Uploaded {local_file_path} to gs://{bucket_name}/{gcs_path}"


def upload_raw_files(bucket_name, load_date, time_suffix, raw_data_dir="data/raw", max_workers=4):
    if not os.path.exists(raw_data_dir):
        raise FileNotFoundError(f"Source directory not found: {raw_data_dir}")

    files = [f for f in os.listdir(raw_data_dir) if f.endswith(".csv")]
    if not files:
        raise FileNotFoundError(f"No CSV files found in {raw_data_dir}")

    client = storage.Client()
    upload_tasks = []

    for filename in files:
        table_name = get_table_name(filename)
        base_name = filename.replace(".csv", "")
        gcs_filename = f"{base_name}_{time_suffix}.csv"
        gcs_path = f"{table_name}/load_date={load_date}/{gcs_filename}"
        local_path = os.path.join(raw_data_dir, filename)
        upload_tasks.append((local_path, gcs_path))

    print(f"Uploading {len(upload_tasks)} files to gs://{bucket_name} with Hive partitioning...")
    with ThreadPoolExecutor(max_workers=min(len(upload_tasks), max_workers)) as executor:
        futures = [executor.submit(upload_file_to_gcs, client, bucket_name, local_path, gcs_path)
                   for local_path, gcs_path in upload_tasks]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Uploading files"):
            try:
                print(future.result())
            except Exception as exc:
                print(f"Upload failed: {exc}")


def generate_customers():
    print("📦 Generating customers...")
    email_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
    customers = []

    for i in tqdm(range(1, NUM_CUSTOMERS + 1), desc="Customers"):
        name = fake.name()
        domain = random.choice(email_domains)
        local_part = name.lower().replace(" ", ".")
        email = f"{local_part}@{domain}"
        country = "Nigeria" if random.random() > 0.03 else None
        created_at = fake.date_time_between(start_date='-3y', end_date='-6m')
        customers.append([i, name, email, country, created_at])

    df_customers = pd.DataFrame(customers, columns=[
        "customer_id", "name", "email", "country", "created_at"
    ])
    df_customers = pd.concat([df_customers, df_customers.sample(frac=0.01)])
    output_path = "data/raw/src_customers.csv"
    df_customers.to_csv(output_path, index=False)
    print("✅ Customers saved")
    return output_path


def generate_transactions():
    print("💳 Generating transactions... (this will take time)")
    customer_ids = generate_skewed_ids(NUM_CUSTOMERS, NUM_TRANSACTIONS)
    transactions = []

    for i in tqdm(range(1, NUM_TRANSACTIONS + 1), desc="Transactions"):
        cust_id = int(customer_ids[i - 1])
        base_amount = np.random.exponential(scale=2000)
        if random.random() < 0.1:
            base_amount *= 10

        amount = round(base_amount, 2)
        if random.random() < 0.03:
            amount = None

        currency = random.choice(["NGN", "ngn", "Naira", None])
        tx_time = fake.date_time_between(start_date='-1y', end_date='now')
        transactions.append([i, cust_id, amount, currency, tx_time])

    print("🔁 Injecting duplicates...")
    transactions += random.sample(transactions, int(0.02 * NUM_TRANSACTIONS))
    df_transactions = pd.DataFrame(transactions, columns=[
        "transaction_id", "customer_id", "amount", "currency", "transaction_date"
    ])
    output_path = "data/raw/src_billing_transactions.csv"
    df_transactions.to_csv(output_path, index=False)
    print("✅ Transactions saved")
    return output_path


def generate_sessions():
    print("🌐 Generating sessions... (largest step)")
    customer_ids_sessions = generate_skewed_ids(NUM_CUSTOMERS, NUM_SESSIONS)
    sessions = []

    for i in tqdm(range(1, NUM_SESSIONS + 1), desc="Sessions"):
        cust_id = int(customer_ids_sessions[i - 1])
        start = fake.date_time_between(start_date='-1y', end_date='now')

        if random.random() < 0.7:
            duration = random.randint(10, 300)
        elif random.random() < 0.9:
            duration = random.randint(300, 1800)
        else:
            duration = random.randint(1800, 7200)

        end = start + pd.Timedelta(seconds=duration)
        if random.random() < 0.02:
            end = start - pd.Timedelta(seconds=random.randint(1, 300))

        data_used = duration * random.uniform(0.01, 0.2)
        if random.random() < 0.01:
            data_used *= 50
        if random.random() < 0.02:
            data_used = None

        sessions.append([
            i,
            cust_id,
            start,
            end,
            round(data_used, 2) if data_used else None
        ])

    print("🔁 Injecting session duplicates...")
    sessions += random.sample(sessions, int(0.02 * NUM_SESSIONS))
    df_sessions = pd.DataFrame(sessions, columns=[
        "session_id", "customer_id", "start_time", "end_time", "data_used_mb"
    ])
    output_path = "data/raw/src_network_sessions.csv"
    df_sessions.to_csv(output_path, index=False)
    print("✅ Sessions saved")
    return output_path


def main(bucket_name=None, load_date=None, upload=False, max_workers=4):
    if load_date is None:
        load_date = datetime.now().strftime('%Y%m%d')
    time_suffix = datetime.now().strftime('%H%M%S')

    os.makedirs('data/raw', exist_ok=True)
    generated_files = [
        generate_customers(),
        generate_transactions(),
        generate_sessions(),
    ]

    print("\n🔥 DATA GENERATION COMPLETE")
    print("Files created:")
    for path in generated_files:
        print(f"- {os.path.basename(path)}")

    if upload:
        upload_raw_files(bucket_name=bucket_name, load_date=load_date, time_suffix=time_suffix, max_workers=max_workers)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate raw CSV data and optionally upload to GCS using Hive partitioning.")
    parser.add_argument("--bucket", help="GCS bucket name for upload, e.g., datatel_comms_bucket")
    parser.add_argument("--load_date", help="Load date in YYYYMMDD format. Defaults to today.")
    parser.add_argument("--upload", help="Upload generated files to GCS.", action="store_true")
    parser.add_argument("--workers", help="Number of parallel upload workers.", type=int, default=4)
    args = parser.parse_args()

    if args.upload and not args.bucket:
        parser.error("--bucket is required when --upload is set")

    main(bucket_name=args.bucket, load_date=args.load_date, upload=args.upload, max_workers=args.workers)
