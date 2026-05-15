import argparse
import os
import random
from datetime import datetime

import numpy as np
import pandas as pd
from faker import Faker
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


def generate_customers(raw_data_dir="data/raw"):
    print("📦 Generating customers...")
    email_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
    customers = []

    for i in tqdm(range(1, NUM_CUSTOMERS + 1), desc="Customers"):
        name = fake.name()
        domain = random.choice(email_domains)
        local_part = name.lower().replace(" ", ".")
        email = f"{local_part}@{domain}"
        country = "Nigeria" if random.random() > 0.03 else None
        created_at = fake.date_time_between(start_date="-3y", end_date="-6m")
        customers.append([i, name, email, country, created_at])

    df_customers = pd.DataFrame(
        customers, columns=["customer_id", "name", "email", "country", "created_at"]
    )
    df_customers = pd.concat([df_customers, df_customers.sample(frac=0.01)])
    output_path = os.path.join(raw_data_dir, "src_customers.csv")
    df_customers.to_csv(output_path, index=False)
    print("✅ Customers saved")
    return output_path


def generate_transactions(raw_data_dir="data/raw"):
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
        tx_time = fake.date_time_between(start_date="-1y", end_date="now")
        transactions.append([i, cust_id, amount, currency, tx_time])

    print("🔁 Injecting duplicates...")
    transactions += random.sample(transactions, int(0.02 * NUM_TRANSACTIONS))
    df_transactions = pd.DataFrame(
        transactions,
        columns=[
            "transaction_id",
            "customer_id",
            "amount",
            "currency",
            "transaction_date",
        ],
    )
    output_path = os.path.join(raw_data_dir, "src_billing_transactions.csv")
    df_transactions.to_csv(output_path, index=False)
    print("✅ Transactions saved")
    return output_path


def generate_sessions(raw_data_dir="data/raw"):
    print("🌐 Generating sessions... (largest step)")
    customer_ids_sessions = generate_skewed_ids(NUM_CUSTOMERS, NUM_SESSIONS)
    sessions = []

    for i in tqdm(range(1, NUM_SESSIONS + 1), desc="Sessions"):
        cust_id = int(customer_ids_sessions[i - 1])
        start = fake.date_time_between(start_date="-1y", end_date="now")

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

        sessions.append(
            [i, cust_id, start, end, round(data_used, 2) if data_used else None]
        )

    print("🔁 Injecting session duplicates...")
    sessions += random.sample(sessions, int(0.02 * NUM_SESSIONS))
    df_sessions = pd.DataFrame(
        sessions,
        columns=["session_id", "customer_id", "start_time", "end_time", "data_used_mb"],
    )
    output_path = os.path.join(raw_data_dir, "src_network_sessions.csv")
    df_sessions.to_csv(output_path, index=False)
    print("✅ Sessions saved")
    return output_path


def generate_data(raw_data_dir="data/raw"):
    os.makedirs(raw_data_dir, exist_ok=True)
    generated_files = [
        generate_customers(raw_data_dir),
        generate_transactions(raw_data_dir),
        generate_sessions(raw_data_dir),
    ]

    print("\n🔥 DATA GENERATION COMPLETE")
    print("Files created:")
    for path in generated_files:
        print(f"- {os.path.basename(path)}")
    return generated_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate raw CSV data for the datatel communications pipeline."
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        help="Local raw data directory for generated CSVs.",
    )
    args = parser.parse_args()

    generate_data(raw_data_dir=args.raw_dir)
