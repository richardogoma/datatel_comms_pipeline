# Project Brief: Datatel Comms Multi-Layered Google Cloud Data Pipeline

## Project Overview
This project establishes a robust, multi-layered data pipeline on Google Cloud Platform (GCP) designed to transform raw telecommunications data (billing, customers, and network sessions) into a high-fidelity curated data warehouse for business intelligence and analytical SQL querying.

------------------------
## Objectives
*   **Automated Ingestion:** Standardize data extraction and quality reporting via a custom Python utility.
*   **Scalable Transformation:** Implement a medallions-style architecture (Raw -> Enriched -> Curated) within BigQuery.
*   **Data Integrity:** Ensure data quality through staging, de-duplication, and type-casting.
*   **Analytical Readiness:** Deliver a unified `dw_user_analytics` table for downstream consumption.

--------------------------
## Technical Architecture

<img width="1376" height="768" alt="a_professional_high_fidelity_technical_architecture_diagram_of_a_multi_layered" src="https://github.com/user-attachments/assets/3c3f55c9-9f86-4847-b794-d12145c60aaf" />


### Layer 1: Data Ingestion (Landing Zone)
*   **Process:** Generates source data, performs Data Quality (DQ) checks, and uploads CSVs to Google Cloud Storage (GCS) buckets.
*   **Outputs:** Data Quality Report, CSV files in GCS.
*   **GCS Buckets:** 
    *   `gs://datatel_comms_landing/billing_transactions/*`: Contains billing transaction data in CSV format.
    *   `gs://datatel_comms_landing/customers/*`: Contains customer data in CSV format.
    *   `gs://datatel_comms_landing/network_sessions/*`: Contains network session data in CSV format.

### Layer 2: Raw Zone (BigQuery)
*   **External Tables (src_):** 1:1 mapping to GCS buckets for schema-on-read access.
*   **Staging Tables (stg_):** Incremental tables responsible for:
    *   Cleaning and casting (e.g., timestamps, floats).
    *   De-duplication by primary keys (transaction_id, customer_id, session_id).
    *   Standardizing formats (emails, country names).

### Layer 3: Enriched Zone (BigQuery)
* This layer contains business-level aggregations and transformations, creating more valuable and insightful datasets.
*   **Aggregations:** Business-level metrics including:
    *   `agg_user_revenue` & `agg_user_usage`
    *   `agg_arpu` (Average Revenue Per User)
    *   `agg_country_revenue`
*   **Views:** `session_buckets` for categorizing session duration (short/medium/long).

### Layer 4: Curated Zone (BigQuery)
* This is the final layer, providing a single, wide table that is optimized for analytics and business intelligence.
*   **The Data Warehouse:** `dw_user_analytics`
*   **Purpose:** A wide, flat table joining all enriched metrics with customer dimensions, optimized for BI tools and SQL analysis.

------------------------
## Executing the Pipeline

For the data generation and upload utility, use `uv` Python package manager to run commands from the project root.

Generate raw data and validate:

```powershell
uv run main.py --generate --validate
```

Upload raw files to GCS:

```powershell
uv run main.py --upload --bucket datatel_comms_landing
```

Run the full workflow in order: generate, validate, then upload.

```powershell
uv run main.py --run-all --bucket datatel_comms_landing
```

On BigQuery, simply execute the pipeline from the GUI. 

--------------------------
## Deliverables

### Deliverable - Stage 1

*What problems did you find in the data quality check or initial validation stage?*
---------------

#### src_billing_transactions — Duplicate `transaction_id` values

**Problem found:**
The dataset contains duplicate `transaction_id` records. A total of **30,000 unique transaction IDs** appear more than once. This suggests possible retry events, duplicate ingestion during data loads, or synchronization issues in the source system.

**Risk to downstream aggregations:**
Duplicate transactions will inflate billing and revenue calculations because the same transaction may be counted multiple times. Aggregated customer spend, total revenue, and reconciliation reports will become inaccurate, creating a high risk for financial reporting and downstream analytics.

---

#### src_network_sessions — Duplicate `session_id` values

**Problem found:**
The dataset contains duplicate `session_id` records. A total of **60,000 unique session IDs** appear more than once. This may indicate repeated logging, ingestion duplication, or ETL processing errors.

**Risk to downstream aggregations:**
Duplicate sessions will cause overcounting in session-based metrics and network usage calculations. Aggregated data usage, session counts, and SLA metrics may be overstated, leading to inaccurate operational reporting and distorted customer usage analytics.


### Deliverable - Stage 2

*Why did you chose `ROW_NUMBER()` rather than `SELECT DISTINCT` for deduplication?*
---------------

For the `stg_*` tables, `ROW_NUMBER()` was used instead of `SELECT DISTINCT` because it provides controlled and deterministic deduplication.

`SELECT DISTINCT` only removes rows that are completely identical across all selected columns. If multiple records share the same business key (for example, `customer_id`) but contain different attribute values, `SELECT DISTINCT` would keep all versions because they are not exact duplicates.

Using `ROW_NUMBER()` with `PARTITION BY` and `ORDER BY` allows the pipeline to define which record should be retained. The logic groups records by the entity identifier, orders them by the most recent `load_date`, and keeps only the latest version:

```sql
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY entity_id
    ORDER BY load_date DESC
) = 1
```

This approach ensures that when multiple versions of the same record exist, only the most recent and relevant record is preserved in the staging layer.


### Deliverable - Stage 3

*How did you handle the divide-by-zero risk and why is `NULLIF` the appropriate method?*
-----------------

The ARPU calculation is `total_revenue / num_months`. If a customer has no transactions, `num_months` would be 0, causing a "division by zero" error.

The expression `NULLIF(num_months, 0)` elegantly solves this. If `num_months` is 0, `NULLIF` returns `NULL`; otherwise, it returns the `num_months` value. In SQL, dividing any number by `NULL` results in `NULL`, not an error.


### Deliverable -  Stage 4

*Why `LEFT JOIN`s rather than `INNER JOIN`s, and what would break if you used `INNER JOIN`s instead?*
------------------

The join strategy uses `LEFT JOIN` to ensure the final table includes **every customer**, making the `stg_customers` table the source of truth.

If `INNER JOIN` were used instead, any customer without activity (e.g., a new user with no billing transactions) would be completely dropped from the final `dw_user_analytics` table. This would break the analysis by creating an incomplete view of the customer base.


### Deliverable -  Stage 5

*For the churn risk query, what are the limitations of the current rule, and how would you improve it?*
------------------

The churn risk rule implemented is a good starting point because it combines both engagement (`total_sessions`) and monetization (`total_revenue`) instead of relying on a single metric. Adding the `created_at` condition also improves the logic by preventing newly registered customers from being incorrectly classified as “High Risk” before they have had enough time to use the service.

However, the rule can still produce false positives for legitimate low-usage customers. For example, some customers may only use the service occasionally, such as travelers, backup SIM users, or seasonal users, yet still intend to remain active. A customer could also have few sessions but high-value future potential.

To improve the model further, the churn logic could incorporate:

* **Recency of activity** (days since last session or transaction).
* **Customer tenure** (how long the customer has been registered).
* **Usage trends over time** instead of static totals.
* **Behavioral segmentation** to distinguish casual users from disengaged users.

Overall, the query demonstrates a more realistic churn detection approach by introducing a customer age threshold, which reduces unfair classification of newly onboarded users.


### Deliverable -  Stage 6

*How you would extend the incremental pattern to cover the staging tables, `stg_sessions` and `stg_customers`?*
------------------

The incremental pattern is implemented in the `stg_billing`, `stg_customers`, and `stg_sessions` tables to efficiently process only new data, rather than rebuilding the tables on every run.

This is achieved by:

1. **Filtering for New Records:** A `WHERE` clause filters the source data to select only records with a timestamp (e.g., `transaction_date`) that is newer than the most recent record already in the target table.
2. **Merging with a Unique Key:** A `uniqueKey` (e.g., `transaction_id`) is defined, which instructs Dataform to perform a `MERGE` operation. This automatically updates existing rows if a match is found and inserts the record if it's new.

*Does this mean the use of `ROW_NUMBER` is redundant?*
-------------------

Think of a scenario where the source data for a single day contains the same `transaction_id` twice (perhaps an initial record and then a correction sent a few hours later). The incremental `WHERE` clause would select both of these records because they are both new.

`ROW_NUMBER()` then steps in to resolve this conflict. By partitioning by `transaction_id` and ordering by `load_date`, it ensures that only the single most recent version of that transaction from the new batch is chosen, preventing duplicates from entering your final table.

In short:

* Incremental `WHERE`: Filters for new data to improve efficiency.
* `ROW_NUMBER()`: Deduplicates the new data to ensure correctness.
