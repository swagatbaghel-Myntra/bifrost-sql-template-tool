SELECT
    load_date,
    brand,
    COUNT(DISTINCT sku_id) AS active_skus,
    SUM(orders) AS total_orders,
    SUM(revenue) AS total_revenue
FROM commerce.sku_daily_metrics
WHERE load_date BETWEEN {{ start_date }} AND {{ end_date }}
  AND brand IN ({{ brands | sql_list }})
GROUP BY
    load_date,
    brand
ORDER BY
    load_date,
    brand
