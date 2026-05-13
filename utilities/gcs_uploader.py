import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.cloud import storage
from tqdm import tqdm


def upload_file_to_gcs(client, bucket_name, local_file_path, gcs_path):
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(local_file_path)
    return f"Uploaded {local_file_path} to gs://{bucket_name}/{gcs_path}"


def upload_raw_files(
    bucket_name,
    load_date,
    time_suffix,
    raw_data_dir="data/raw",
    max_workers=4,
):
    if not os.path.exists(raw_data_dir):
        raise FileNotFoundError(f"Source directory not found: {raw_data_dir}")

    files = [f for f in os.listdir(raw_data_dir) if f.endswith(".csv")]
    if not files:
        raise FileNotFoundError(f"No CSV files found in {raw_data_dir}")

    client = storage.Client()
    upload_tasks = []

    for filename in files:
        table_name = filename.replace("src_", "").replace(".csv", "")
        base_name = filename.replace(".csv", "")
        gcs_filename = f"{base_name}_{time_suffix}.csv"
        gcs_path = f"{table_name}/load_date={load_date}/{gcs_filename}"
        local_path = os.path.join(raw_data_dir, filename)
        upload_tasks.append((local_path, gcs_path))

    print(
        f"Uploading {len(upload_tasks)} files to gs://{bucket_name} with Hive partitioning..."
    )
    with ThreadPoolExecutor(max_workers=min(len(upload_tasks), max_workers)) as executor:
        futures = [
            executor.submit(
                upload_file_to_gcs, client, bucket_name, local_path, gcs_path
            )
            for local_path, gcs_path in upload_tasks
        ]

        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Uploading files"
        ):
            try:
                print(future.result())
            except Exception as exc:
                print(f"Upload failed: {exc}")
