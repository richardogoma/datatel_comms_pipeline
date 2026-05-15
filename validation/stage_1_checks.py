import os
from datetime import datetime

import pandas as pd
import great_expectations as gx


def load_raw_csv(filename, raw_dir="data/raw"):
    """Load raw CSV file."""
    path = os.path.join(raw_dir, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Raw CSV not found: {path}")
    return pd.read_csv(path)


# ============================================================================
# 4.1 NULL CHECKS
# ============================================================================


def null_check_billing_transactions(df):
    """
    Check src_billing_transactions for NULL primary identifiers.
    Returns records where transaction_id OR customer_id is NULL.
    """
    null_records = df[
        (df["transaction_id"].isna()) | (df["customer_id"].isna())
    ].copy()
    return null_records


def null_check_network_sessions(df):
    """
    Check src_network_sessions for NULL primary identifiers.
    Returns records where session_id OR customer_id is NULL.
    """
    null_records = df[
        (df["session_id"].isna()) | (df["customer_id"].isna())
    ].copy()
    return null_records


# ============================================================================
# 4.2 DUPLICATE CHECKS
# ============================================================================


def duplicate_check_transactions(df):
    """
    Check src_billing_transactions for duplicate transaction_ids.
    Returns count of occurrences for transaction_ids appearing more than once.
    """
    dup_counts = (
        df.groupby("transaction_id", dropna=False)
        .size()
        .reset_index(name="count")
    )
    dup_counts = dup_counts[dup_counts["count"] > 1].sort_values(
        "count", ascending=False
    )
    return dup_counts


def duplicate_check_sessions(df):
    """
    Check src_network_sessions for duplicate session_ids.
    Returns count of occurrences for session_ids appearing more than once.
    """
    dup_counts = (
        df.groupby("session_id", dropna=False)
        .size()
        .reset_index(name="count")
    )
    dup_counts = dup_counts[dup_counts["count"] > 1].sort_values(
        "count", ascending=False
    )
    return dup_counts


# ============================================================================
# RISK ASSESSMENT NOTES
# ============================================================================


def write_null_check_note(
    null_billing_count, null_sessions_count, results_dir
):
    """Write risk assessment for NULL values."""
    note = f"""
NULL CHECK FINDINGS
===================

src_billing_transactions - NULL Primary Identifiers
---------------------------------------------------
Records found: {null_billing_count}

Risk Assessment:
  A transaction without a customer_id cannot be attributed to anyone. 
  If loaded as-is:
    - Revenue may be silently dropped from aggregations.
    - Or misattributed to the wrong customer, inflating their totals.
    - Total revenue counts will be understated by {null_billing_count} transactions.
  
Impact on Downstream: HIGH
  - Billing reports will be inaccurate.
  - Revenue per customer will be skewed.
  - Reconciliation will be impossible for these {null_billing_count} records.

src_network_sessions - NULL Primary Identifiers
------------------------------------------------
Records found: {null_sessions_count}

Risk Assessment:
  A session without a session_id or customer_id is orphaned data.
  If loaded as-is:
    - Session counts and data usage metrics will be understated.
    - Customer engagement metrics will exclude {null_sessions_count} sessions.
    - Network capacity planning may miss traffic patterns.

Impact on Downstream: HIGH
  - Session-based analytics will be incomplete.
  - Customer activity reports will undercount engagement.
  - Data usage trending will be inaccurate.
"""
    note_path = os.path.join(results_dir, "01_null_check_risk_assessment.txt")
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(note)
    print(f"✅ Wrote: {note_path}")


def write_duplicate_check_note(
    dup_transactions_count, dup_sessions_count, results_dir
):
    """Write risk assessment for duplicate IDs."""
    note = f"""
DUPLICATE CHECK FINDINGS
========================

src_billing_transactions - Duplicate transaction_ids
----------------------------------------------------
Unique transaction_ids with duplicates: {dup_transactions_count}

Risk Assessment:
  A transaction_id appearing multiple times indicates:
    - Retry events (system resubmitted the same transaction).
    - Data load errors (same record inserted twice).
    - Clock skew or async processing issues.
  
  If loaded as-is:
    - Billing totals will be inflated (double or triple counting).
    - Revenue per customer will be overstated.
    - Reconciliation with source system will fail.

Impact on Downstream: CRITICAL
  - Revenue reports will be incorrect.
  - Customer billing queries will show duplicate charges.
  - Financial reconciliation will not balance.
  
  Decision Required in Staging Layer:
    - Keep only the first occurrence (earliest timestamp)?
    - Keep only the most recent?
    - Mark as retry and aggregate distinctly?

src_network_sessions - Duplicate session_ids
---------------------------------------------
Unique session_ids with duplicates: {dup_sessions_count}

Risk Assessment:
  A session_id appearing multiple times indicates:
    - Logging retries (same session logged twice).
    - Data ingestion issues (duplicate rows from source).
    - ETL errors.
  
  If loaded as-is:
    - Session counts will be overstated.
    - Data usage (MB) will be doubled or tripled.
    - Customer session counts will be inflated.

Impact on Downstream: HIGH
  - Network usage reports will be inaccurate.
  - Session-based SLA metrics will be wrong.
  - Customer data allowance calculations will be skewed.
  
  Decision Required in Staging Layer:
    - Deduplicate by session_id (keep first or most recent)?
    - Flag as retries for separate analysis?
    - Investigate root cause before deduplication?
"""
    note_path = os.path.join(
        results_dir, "02_duplicate_check_risk_assessment.txt"
    )
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(note)
    print(f"✅ Wrote: {note_path}")


# ============================================================================
# VALIDATION REPORTING (Great Expectations)
# ============================================================================


def run_gx_validation(df, table_name):
    """Run GX expectations for validation reporting."""
    context = gx.get_context()

    datasource_name = "my_pandas_datasource"

    # Create datasource if missing
    try:
        datasource = context.data_sources.get(datasource_name)
    except Exception:
        datasource = context.data_sources.add_pandas(name=datasource_name)

    asset_name = f"{table_name}_asset"

    # Create asset if missing
    try:
        asset = datasource.get_asset(asset_name)
    except Exception:
        asset = datasource.add_dataframe_asset(name=asset_name)

    batch_definition_name = f"{table_name}_batch"

    # Create batch definition if missing
    try:
        batch_definition = asset.get_batch_definition(batch_definition_name)
    except Exception:
        batch_definition = asset.add_batch_definition_whole_dataframe(
            batch_definition_name
        )

    # Get batch
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    suite_name = f"{table_name}_suite"

    validator = context.get_validator(
        batch=batch,
        create_expectation_suite_with_name=suite_name,
    )

    # Add expectations
    if table_name == "src_billing_transactions":
        validator.expect_column_values_to_not_be_null("transaction_id")
        validator.expect_column_values_to_not_be_null("customer_id")
        validator.expect_column_values_to_be_unique("transaction_id")

    elif table_name == "src_network_sessions":
        validator.expect_column_values_to_not_be_null("session_id")
        validator.expect_column_values_to_not_be_null("customer_id")
        validator.expect_column_values_to_be_unique("session_id")

    # Run validation
    results = validator.validate()

    # Save suite
    context.suites.add_or_update(validator.expectation_suite)

    # Build docs
    context.build_data_docs()

    # Docs URL
    docs_sites = context.get_docs_sites_urls()
    docs_url = (
        docs_sites[0]["site_url"] if docs_sites else "No docs generated"
    )

    return results, docs_url


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def run_stage_1_checks(raw_dir="data/raw", results_dir="validation/results"):
    """
    Stage 1 Data Quality Checks.

    Performs null and duplicate checks on source tables without modifying data.
    Surfaces all problems and writes risk assessments.
    """
    os.makedirs(results_dir, exist_ok=True)

    # Load source files
    billing_df = load_raw_csv("src_billing_transactions.csv", raw_dir)
    sessions_df = load_raw_csv("src_network_sessions.csv", raw_dir)

    # ========================================================================
    # 4.1 NULL CHECKS
    # ========================================================================
    print("\n📋 Running null checks...")

    null_billing = null_check_billing_transactions(billing_df)
    null_sessions = null_check_network_sessions(sessions_df)

    null_billing.to_csv(
        os.path.join(results_dir, "null_src_billing_transactions.csv"),
        index=False,
    )
    print(f"  ✅ Found {len(null_billing)} NULL records in billing")

    null_sessions.to_csv(
        os.path.join(results_dir, "null_src_network_sessions.csv"),
        index=False,
    )
    print(f"  ✅ Found {len(null_sessions)} NULL records in sessions")

    # ========================================================================
    # 4.2 DUPLICATE CHECKS
    # ========================================================================
    print("\n📋 Running duplicate checks...")

    dup_transactions = duplicate_check_transactions(billing_df)
    dup_sessions = duplicate_check_sessions(sessions_df)

    dup_transactions.to_csv(
        os.path.join(
            results_dir, "duplicate_src_billing_transactions.csv"
        ),
        index=False,
    )
    print(
        f"  ✅ Found {len(dup_transactions)} duplicate transaction_ids"
    )

    dup_sessions.to_csv(
        os.path.join(results_dir, "duplicate_src_network_sessions.csv"),
        index=False,
    )
    print(f"  ✅ Found {len(dup_sessions)} duplicate session_ids")

    # ========================================================================
    # RISK ASSESSMENT NOTES
    # ========================================================================
    print("\n📝 Writing risk assessments...")

    write_null_check_note(len(null_billing), len(null_sessions), results_dir)
    write_duplicate_check_note(
        len(dup_transactions), len(dup_sessions), results_dir
    )

    # ========================================================================
    # GREAT EXPECTATIONS VALIDATION
    # ========================================================================
    print("\n🔍 Running Great Expectations validation...")

    billing_results, billing_docs = run_gx_validation(
        billing_df, "src_billing_transactions"
    )
    sessions_results, sessions_docs = run_gx_validation(
        sessions_df, "src_network_sessions"
    )

    # ========================================================================
    # SUMMARY REPORT
    # ========================================================================
    summary = f"""
Stage 1 Data Quality Check Complete
====================================

Null Checks:
  - src_billing_transactions: {len(null_billing)} records with NULL primary identifiers
  - src_network_sessions: {len(null_sessions)} records with NULL primary identifiers

Duplicate Checks:
  - src_billing_transactions: {len(dup_transactions)} unique transaction_ids appearing >1 time
  - src_network_sessions: {len(dup_sessions)} unique session_ids appearing >1 time

Great Expectations Results:
  - src_billing_transactions: Success={billing_results.success}
  - src_network_sessions: Success={sessions_results.success}

Output Files:
  ✅ null_src_billing_transactions.csv
  ✅ null_src_network_sessions.csv
  ✅ duplicate_src_billing_transactions.csv
  ✅ duplicate_src_network_sessions.csv
  ✅ 01_null_check_risk_assessment.txt
  ✅ 02_duplicate_check_risk_assessment.txt
  ✅ Great Expectations Data Docs (see {billing_docs})

Generated: {datetime.now().isoformat()}
"""

    summary_path = os.path.join(
        results_dir, "00_stage_1_quality_summary.txt"
    )
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)

    print(summary)
    print(f"✅ Summary written to: {summary_path}")

    return {
        "null_billing_count": len(null_billing),
        "null_sessions_count": len(null_sessions),
        "duplicate_transactions_count": len(dup_transactions),
        "duplicate_sessions_count": len(dup_sessions),
        "summary_path": summary_path,
    }

if __name__ == "__main__":
    run_stage_1_checks()
