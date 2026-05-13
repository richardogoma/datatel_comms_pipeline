# Datatel Comms Pipeline

## Running the pipeline

Use `uv` to run commands from the project root.

Generate raw data and validate:

```powershell
uv run main.py --generate --validate
```

Upload raw files to GCS:

```powershell
uv run main.py --upload --bucket <your-gcs-bucket>
```

Run the full workflow in order: generate, validate, then upload.

```powershell
uv run main.py --run-all --bucket <your-gcs-bucket>
```

## Validation outputs

Stage 1 validation performs Python-based null and duplicate checks, writes findings and risk assessments, and generates Great Expectations reports.

**Output files in `validation/results/`:**

1. **Null Check Results**
   - `null_src_billing_transactions.csv` — Records where transaction_id or customer_id is NULL
   - `null_src_network_sessions.csv` — Records where session_id or customer_id is NULL

2. **Duplicate Check Results**
   - `duplicate_src_billing_transactions.csv` — transaction_ids appearing more than once (with counts)
   - `duplicate_src_network_sessions.csv` — session_ids appearing more than once (with counts)

3. **Risk Assessments**
   - `01_null_check_risk_assessment.txt` — Impact analysis for NULL primary identifiers
   - `02_duplicate_check_risk_assessment.txt` — Impact analysis for duplicate IDs

4. **Summary & Docs**
   - `00_stage_1_quality_summary.txt` — Overview of all findings
   - Great Expectations Data Docs: HTML reports in `gx/uncommitted/data_docs/local_site/` (open `index.html`)
