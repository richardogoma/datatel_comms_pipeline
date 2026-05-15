import argparse
import truststore
from datetime import datetime

from utilities.data_generator import generate_data
from utilities.gcs_uploader import upload_raw_files
from validation.stage_1_checks import run_stage_1_checks

truststore.inject_into_ssl()

def main(
    generate=False,
    upload=False,
    validate=False,
    run_all=False,
    bucket_name=None,
    load_date=None,
    workers=4,
    raw_dir="data/raw",
    results_dir="validation/results",
):
    if load_date is None:
        load_date = datetime.now().strftime("%Y%m%d")

    if run_all:
        generate = True
        validate = True
        upload = True

    if generate:
        generate_data(raw_data_dir=raw_dir)

    if validate:
        run_stage_1_checks(raw_dir=raw_dir, results_dir=results_dir)

    if upload:
        upload_raw_files(
            bucket_name=bucket_name,
            load_date=load_date,
            time_suffix=datetime.now().strftime("%H%M%S"),
            raw_data_dir=raw_dir,
            max_workers=workers,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline entrypoint for data generation, GCS upload, and Stage 1 validation."
    )
    parser.add_argument(
        "--generate",
        help="Generate raw source CSV files.",
        action="store_true",
    )
    parser.add_argument(
        "--validate",
        help="Run Stage 1 data quality checks.",
        action="store_true",
    )
    parser.add_argument(
        "--upload",
        help="Upload raw CSV files to GCS.",
        action="store_true",
    )
    parser.add_argument(
        "--run-all",
        help="Run generate, validate, and upload in sequence.",
        action="store_true",
    )
    parser.add_argument(
        "--bucket",
        help="GCS bucket name for upload, e.g., datatel_comms_bucket.",
    )
    parser.add_argument(
        "--load-date",
        help="Load date in YYYYMMDD format. Defaults to today.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Parallel workers for upload.",
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        help="Local raw data directory.",
    )
    parser.add_argument(
        "--results-dir",
        default="validation/results",
        help="Local directory to write validation results.",
    )

    args = parser.parse_args()

    if args.run_all:
        args.generate = True
        args.validate = True
        args.upload = True

    if not any([args.generate, args.upload, args.validate]):
        args.generate = True
        args.validate = True

    if args.upload and not args.bucket:
        parser.error("--bucket is required when --upload is set")

    main(
        generate=args.generate,
        upload=args.upload,
        validate=args.validate,
        run_all=args.run_all,
        bucket_name=args.bucket,
        load_date=args.load_date,
        workers=args.workers,
        raw_dir=args.raw_dir,
        results_dir=args.results_dir,
    )
