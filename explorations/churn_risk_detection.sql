-- 8.3  Churn Risk Detection
-- 
-- Add a column called churn_risk. Flag a customer as ‘High Risk’ if they have fewer than 5 total sessions AND less than ₦1,000 in total revenue. All other customers should be labelled ‘Active’.
-- 
-- Once you have written this query, consider: what kinds of legitimate customers might be incorrectly flagged? A customer who just registered yesterday would have very few sessions and no revenue yet. How might you modify the rule to account for this?
SELECT
  t1.customer_id,
  t1.customer_name,
  t1.email,
  t1.country,
  t1.total_revenue,
  t1.total_transactions,
  t1.total_data_used_mb,
  t1.avg_session_duration_sec,
  t1.total_sessions,
  t1.arpu,
  t1.short_sessions,
  t1.medium_sessions,
  t1.long_sessions,
  t1.avg_data_per_session_mb,
  CASE
    WHEN t1.total_sessions < 5 AND t1.total_revenue < 1000 AND t2.created_at < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY) THEN 'High Risk'
    ELSE 'Active'
END
  AS churn_risk
FROM
  `datatel-comms-pipeline-496118`.`curated`.`dw_user_analytics` AS t1
LEFT JOIN
  `datatel-comms-pipeline-496118`.`raw`.`stg_customers` AS t2
ON
  t1.customer_id = t2.customer_id;