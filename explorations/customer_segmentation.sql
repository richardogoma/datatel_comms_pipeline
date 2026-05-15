-- 8.2  Customer Segmentation
-- 
-- Add a column called customer_segment to a query on dw_user_analytics using the following rules:
-- 
-- ‘High Value’ — customers with total revenue above ₦5,000,000.
-- ‘Mid Value’ — customers with total revenue above ₦1,000,000.
-- ‘Low Value’ — all other customers.
SELECT
  customer_id,
  customer_name,
  email,
  country,
  total_revenue,
  total_transactions,
  total_data_used_mb,
  avg_session_duration_sec,
  total_sessions,
  arpu,
  short_sessions,
  medium_sessions,
  long_sessions,
  avg_data_per_session_mb,
  CASE
    WHEN total_revenue > 5000000 THEN 'High Value'
    WHEN total_revenue > 1000000 THEN 'Mid Value'
    ELSE 'Low Value'
END
  AS customer_segment
FROM
  `datatel-comms-pipeline-496118`.`curated`.`dw_user_analytics`;