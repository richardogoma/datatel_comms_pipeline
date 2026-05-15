-- 8.4  Revenue vs. Usage Mismatch
-- 
-- Write a query that returns customers who have consumed more than 10,000 MB of data but have generated less than ₦500 in revenue. These users may be on outdated or under-priced legacy plans.
SELECT
  t0.customer_id,
  t0.customer_name,
  t0.email,
  t0.total_data_used_mb,
  t0.total_revenue
FROM
  `datatel-comms-pipeline-496118`.`curated`.`dw_user_analytics` AS t0
WHERE
  t0.total_data_used_mb > 10000
  AND t0.total_revenue < 500;