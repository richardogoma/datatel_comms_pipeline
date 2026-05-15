-- Data Freshness Check - Staging tables
SELECT
  'stg_billing' AS table_name,
  MAX(transaction_date) AS most_recent_timestamp
FROM
  `datatel-comms-pipeline-496118`.`raw`.`stg_billing`
UNION ALL
SELECT
  'stg_customers' AS table_name,
  MAX(created_at) AS most_recent_timestamp
FROM
  `datatel-comms-pipeline-496118`.`raw`.`stg_customers`
UNION ALL
SELECT
  'stg_sessions' AS table_name,
  MAX(end_time) AS most_recent_timestamp
FROM
  `datatel-comms-pipeline-496118`.`raw`.`stg_sessions`;