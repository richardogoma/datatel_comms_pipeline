-- 8.1  Top Customers by Revenue
--
-- Return the top 10 customers ranked by total lifetime revenue, highest first.

-- This SQL query retrieves the customer ID, name, and total revenue from the `dw_user_analytics` table.
-- It then sorts these customers by their total revenue in descending order. Finally, it displays only the top 10 customers who have generated the highest revenue.
SELECT
  t0.customer_id,
  t0.customer_name,
  t0.total_revenue
FROM
  `datatel-comms-pipeline-496118`.`curated`.`dw_user_analytics` AS t0
ORDER BY
  t0.total_revenue DESC
LIMIT
  10;